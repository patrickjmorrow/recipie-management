"""Curated, rotating sections for the landing page.

A registry of `SectionDef`s, each with a query builder over `Recipe`. The browse
endpoint randomly samples a few per request so the landing page stays fresh. All
builders eager-load tags and return whole `Recipe` rows so they serialize directly
as `RecipeSummary`, exactly like `recipes.list_recipes`.

Nutrition sections rely on the per-serving macros cached on the recipe row
(see `recipes._store_cached_macros`); they only surface recipes whose macros have
been computed, and self-heal as recipes are viewed/edited.
"""

import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial

from sqlalchemy import Integer, cast, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ingredient import Ingredient, RecipeIngredient
from app.models.recipe import Recipe

# Min reviews before a recipe is eligible for "Crowd Favorites" — one stray 5-star
# rating shouldn't out-rank a well-reviewed recipe.
MIN_REVIEWS = 1


@dataclass(frozen=True)
class SectionDef:
    key: str
    title: str
    subtitle: str | None
    build: Callable[[AsyncSession, int], Awaitable[list[Recipe]]]


def _base():
    """A Recipe select that eager-loads tags so rows serialize as RecipeSummary."""
    return select(Recipe).options(selectinload(Recipe.tags))


async def _run(db: AsyncSession, stmt) -> list[Recipe]:
    result = await db.execute(stmt)
    return list(result.scalars().all())


# --- builders -------------------------------------------------------------

async def _high_protein(db: AsyncSession, limit: int) -> list[Recipe]:
    stmt = (
        _base()
        .where(Recipe.energy_kcal_per_serving > 0, Recipe.protein_g_per_serving.isnot(None))
        .order_by(Recipe.protein_g_per_serving.desc(), func.random())
        .limit(limit)
    )
    return await _run(db, stmt)


async def _low_carb(db: AsyncSession, limit: int) -> list[Recipe]:
    stmt = (
        _base()
        .where(Recipe.energy_kcal_per_serving > 0, Recipe.carbs_g_per_serving.isnot(None))
        .order_by(Recipe.carbs_g_per_serving.asc(), func.random())
        .limit(limit)
    )
    return await _run(db, stmt)


async def _under_30(db: AsyncSession, limit: int) -> list[Recipe]:
    prep = func.coalesce(cast(Recipe.recipie_metadata["prep_time"].astext, Integer), 0)
    cook = func.coalesce(cast(Recipe.recipie_metadata["cook_time"].astext, Integer), 0)
    total = prep + cook
    stmt = _base().where(total > 0, total <= 30).order_by(func.random()).limit(limit)
    return await _run(db, stmt)


async def _with_ingredient(db: AsyncSession, limit: int, *, term: str) -> list[Recipe]:
    has_ingredient = (
        select(RecipeIngredient.id)
        .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .where(
            RecipeIngredient.recipe_id == Recipe.id,
            Ingredient.name.ilike(f"%{term}%"),
        )
        .correlate(Recipe)
    )
    stmt = _base().where(exists(has_ingredient)).order_by(func.random()).limit(limit)
    return await _run(db, stmt)


async def _top_rated(db: AsyncSession, limit: int) -> list[Recipe]:
    stmt = (
        _base()
        .where(Recipe.avg_rating.isnot(None), Recipe.review_count >= MIN_REVIEWS)
        .order_by(Recipe.avg_rating.desc(), Recipe.review_count.desc())
        .limit(limit)
    )
    return await _run(db, stmt)


async def _fresh(db: AsyncSession, limit: int) -> list[Recipe]:
    stmt = _base().order_by(Recipe.created_at.desc()).limit(limit)
    return await _run(db, stmt)


# --- registry -------------------------------------------------------------

# Ingredient-themed sections; each is its own entry so the random pick rotates them.
_INGREDIENT_THEMES = [
    ("chicken", "Extra Chicken?", "Crowd-pleasers built around chicken"),
    ("pasta", "Pasta Night", "Twirl-worthy bowls of comfort"),
    ("chocolate", "Chocolate Fix", "For when only chocolate will do"),
    ("cheese", "Say Cheese", "Melty, gooey, unapologetically cheesy"),
    ("egg", "Egg-cellent", "Eggs taking center stage"),
]

SECTIONS: list[SectionDef] = [
    SectionDef("high_protein", "Gym Goals", "Highest protein per serving", _high_protein),
    SectionDef("low_carb", "Low Carb Options", "Lightest on the carbs", _low_carb),
    SectionDef("under_30", "In a Hurry? ", "Start to finish in 30 minutes", _under_30),
    SectionDef("top_rated", "Crowd Favorites", "Top rated by the community", _top_rated),
    SectionDef("fresh", "Fresh from the Kitchen", "Just added", _fresh),
    *[
        SectionDef(f"ingredient_{term}", title, subtitle, partial(_with_ingredient, term=term))
        for term, title, subtitle in _INGREDIENT_THEMES
    ],
]


async def build_sections(
    db: AsyncSession, count: int = 5, card_limit: int = 12, min_cards: int = 4
) -> list[tuple[SectionDef, list[Recipe]]]:
    """Randomly pick sections and run their queries, dropping any too-sparse to show.

    Oversamples the registry so dropped (empty/sparse) sections don't shrink the page
    below `count` when enough populated sections exist.
    """
    chosen = random.sample(SECTIONS, k=min(count + 3, len(SECTIONS)))
    out: list[tuple[SectionDef, list[Recipe]]] = []
    for section in chosen:
        recipes = await section.build(db, card_limit)
        if len(recipes) >= min_cards:
            out.append((section, recipes))
        if len(out) >= count:
            break
    return out
