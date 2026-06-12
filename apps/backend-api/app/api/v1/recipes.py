import uuid

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import Integer, case, cast, exists, func, not_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.food import Food
from app.models.ingredient import Ingredient, RecipeIngredient
from app.services.nutrition import (
    MacroLine,
    compute_macros,
    recipe_macros,
    resolve_grams,
    supported_units,
)
from app.models.recipe import Recipe
from app.models.tag import Tag, recipe_tags
from app.models.user import User
from app.schemas.ingredient import RecipeIngredientCreate, RecipeIngredientResponse
from app.schemas.recipe import (
    FridgeMatch,
    MacrosLineResult,
    MacrosPreview,
    MacrosPreviewRequest,
    RecipeCreate,
    RecipeResponse,
    RecipeSummary,
    RecipeUpdate,
)
from app.storage.images import sanitize_image
from app.storage.s3 import delete_file, get_presigned_url, upload_file

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _store_cached_macros(recipe: Recipe, macros) -> None:
    """Persist the per-serving macros used by the nutrition browse sections."""
    recipe.energy_kcal_per_serving = macros.energy_kcal
    recipe.protein_g_per_serving = macros.protein_g
    recipe.carbs_g_per_serving = macros.carbs_g


async def _get_recipe_with_relations(
    recipe_id: uuid.UUID, db: AsyncSession, *, refresh_macros: bool = False
) -> Recipe | None:
    result = await db.execute(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.tags),
            selectinload(Recipe.recipe_ingredients)
            .selectinload(RecipeIngredient.ingredient)
            .joinedload(Ingredient.food)
            .selectinload(Food.portions),
        )
    )
    recipe = result.scalar_one_or_none()
    if recipe is not None:
        # Transient attribute read by RecipeResponse.macros (from_attributes).
        recipe.macros = recipe_macros(recipe)
        # Writes force a refresh; reads lazily backfill the cache when it's never been computed.
        if refresh_macros or recipe.protein_g_per_serving is None:
            _store_cached_macros(recipe, recipe.macros)
            await db.commit()
    return recipe


# Minimum ts_rank for an auto-match to be accepted. Free-text cooking names are
# noisy; below this the guess is more likely wrong than right.
FOOD_MATCH_THRESHOLD = 0.05


async def _match_food(name: str, db: AsyncSession) -> int | None:
    """Best-effort USDA food match for an ingredient name via the search_vec GIN index."""
    rank = func.ts_rank(Food.search_vec, func.plainto_tsquery("english", name)).label("rank")
    result = await db.execute(
        select(Food.id, rank)
        .where(Food.search_vec.op("@@")(func.plainto_tsquery("english", name)))
        .order_by(text("rank DESC"))
        .limit(1)
    )
    hit = result.first()
    return hit.id if hit is not None and hit.rank > FOOD_MATCH_THRESHOLD else None


async def _upsert_ingredient(name: str, food_id: int | None, db: AsyncSession) -> Ingredient:
    """Find-or-create an ingredient, optionally pinning its USDA food link.

    A non-null food_id confirms the link (overwriting any existing match) — note this
    is global, affecting every recipe using the ingredient. With no food_id, a newly
    created ingredient is auto-matched; an existing one is left untouched.
    """
    result = await db.execute(select(Ingredient).where(Ingredient.name == name))
    ingredient = result.scalar_one_or_none()
    if ingredient is None:
        ingredient = Ingredient(name=name, food_id=await _match_food(name, db), food_match="auto")
        db.add(ingredient)
        await db.flush()
    if food_id is not None:
        food = await db.get(Food, food_id)
        if not food:
            raise HTTPException(status_code=404, detail=f"Food {food_id} not found")
        ingredient.food_id = food_id
        ingredient.food_match = "confirmed"
        await db.flush()
    return ingredient


async def _resolve_tags(tag_ids: list[uuid.UUID], db: AsyncSession) -> list[Tag]:
    if not tag_ids:
        return []
    result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
    tags = result.scalars().all()
    if len(tags) != len(tag_ids):
        found = {t.id for t in tags}
        missing = [tid for tid in tag_ids if tid not in found]
        raise HTTPException(status_code=422, detail=f"Tags not found: {missing}")
    deprecated = [t.name for t in tags if t.deprecated_at is not None]
    if deprecated:
        raise HTTPException(status_code=422, detail=f"Tags are deprecated: {deprecated}")
    return list(tags)


@router.get("/", response_model=list[RecipeSummary])
async def list_recipes(
    tag_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    contains_ingredient_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    excludes_ingredient_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    author_id: uuid.UUID | None = None,
    search: str | None = Query(default=None, min_length=1, max_length=100),
    prep_time_max: int | None = Query(default=None, ge=0),
    cook_time_max: int | None = Query(default=None, ge=0),
    servings_min: int | None = Query(default=None, ge=1),
    servings_max: int | None = Query(default=None, ge=1),
    difficulty: str | None = Query(default=None, pattern="^(easy|medium|hard)$"),
    protein_min: float | None = Query(default=None, ge=0),
    protein_max: float | None = Query(default=None, ge=0),
    carbs_min: float | None = Query(default=None, ge=0),
    carbs_max: float | None = Query(default=None, ge=0),
    energy_min: float | None = Query(default=None, ge=0),
    energy_max: float | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Recipe)
    filters = []

    if author_id is not None:
        filters.append(Recipe.author_id == author_id)

    if search is not None:
        filters.append(
            or_(
                Recipe.title.ilike(f"%{search}%"),
                Recipe.description.ilike(f"%{search}%"),
            )
        )

    if tag_ids:
        tag_ids = list(dict.fromkeys(tag_ids))
        tag_count_subq = (
            select(func.count())
            .select_from(recipe_tags)
            .where(
                recipe_tags.c.recipe_id == Recipe.id,
                recipe_tags.c.tag_id.in_(tag_ids),
            )
            .correlate(Recipe)
            .scalar_subquery()
        )
        filters.append(tag_count_subq == len(tag_ids))

    if contains_ingredient_ids:
        contains_ingredient_ids = list(dict.fromkeys(contains_ingredient_ids))
        ing_count_subq = (
            select(func.count())
            .select_from(RecipeIngredient)
            .where(
                RecipeIngredient.recipe_id == Recipe.id,
                RecipeIngredient.ingredient_id.in_(contains_ingredient_ids),
            )
            .correlate(Recipe)
            .scalar_subquery()
        )
        filters.append(ing_count_subq == len(contains_ingredient_ids))

    if excludes_ingredient_ids:
        excl_subq = (
            select(RecipeIngredient.id)
            .where(
                RecipeIngredient.recipe_id == Recipe.id,
                RecipeIngredient.ingredient_id.in_(excludes_ingredient_ids),
            )
            .correlate(Recipe)
        )
        filters.append(not_(exists(excl_subq)))

    if prep_time_max is not None:
        filters.append(cast(Recipe.recipie_metadata["prep_time"].astext, Integer) <= prep_time_max)
    if cook_time_max is not None:
        filters.append(cast(Recipe.recipie_metadata["cook_time"].astext, Integer) <= cook_time_max)
    if servings_min is not None:
        filters.append(cast(Recipe.recipie_metadata["servings"].astext, Integer) >= servings_min)
    if servings_max is not None:
        filters.append(cast(Recipe.recipie_metadata["servings"].astext, Integer) <= servings_max)
    if difficulty is not None:
        filters.append(Recipe.recipie_metadata["difficulty"].astext == difficulty)

    # Macro range filters run against the cached per-serving columns. Recipes
    # with NULL macros are naturally excluded (an unknown macro can't be
    # asserted in range), and the partial indexes cover these comparisons.
    if protein_min is not None:
        filters.append(Recipe.protein_g_per_serving >= protein_min)
    if protein_max is not None:
        filters.append(Recipe.protein_g_per_serving <= protein_max)
    if carbs_min is not None:
        filters.append(Recipe.carbs_g_per_serving >= carbs_min)
    if carbs_max is not None:
        filters.append(Recipe.carbs_g_per_serving <= carbs_max)
    if energy_min is not None:
        filters.append(Recipe.energy_kcal_per_serving >= energy_min)
    if energy_max is not None:
        filters.append(Recipe.energy_kcal_per_serving <= energy_max)

    if filters:
        stmt = stmt.where(*filters)

    stmt = stmt.options(selectinload(Recipe.tags))
    stmt = stmt.order_by(Recipe.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


# Declared before "/{recipe_id}" so "fridge" is never parsed as a UUID.
@router.get("/fridge", response_model=list[FridgeMatch])
async def fridge_recipes(
    have_ingredient_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    max_missing: int = Query(default=5, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """"What's in my fridge": recipes you can make or almost make.

    Given the ingredients you have, rank recipes by the fewest additional
    *non-staple* ingredients needed. Pantry staples (salt, pepper, spices) are
    ignored, so a recipe needing only "flour + salt" counts as ready if you
    have flour. Only recipes with at least one matching ingredient are returned.
    """
    if not have_ingredient_ids:
        return []
    have = list(dict.fromkeys(have_ingredient_ids))

    # Per recipe, over its non-staple ingredients only: count total vs. how many
    # the user has. distinct() guards against an ingredient listed twice.
    total_relevant = func.count(func.distinct(RecipeIngredient.ingredient_id))
    matched = func.count(
        func.distinct(
            case((RecipeIngredient.ingredient_id.in_(have), RecipeIngredient.ingredient_id))
        )
    )
    missing = (total_relevant - matched).label("missing_count")

    stmt = (
        select(
            Recipe,
            total_relevant.label("total_relevant_count"),
            matched.label("matched_count"),
            missing,
        )
        .join(RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id)
        .join(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .where(Ingredient.is_staple.is_(False))
        .group_by(Recipe.id)
        .having(matched > 0)
        .having((total_relevant - matched) <= max_missing)
        .options(selectinload(Recipe.tags))
        .order_by(missing.asc(), matched.desc(), Recipe.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return []

    # Second pass: the actual non-staple ingredient names each recipe still needs.
    recipe_ids = [row.Recipe.id for row in rows]
    missing_stmt = (
        select(RecipeIngredient.recipe_id, Ingredient.name)
        .join(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .where(
            RecipeIngredient.recipe_id.in_(recipe_ids),
            Ingredient.is_staple.is_(False),
            RecipeIngredient.ingredient_id.notin_(have),
        )
    )
    missing_by_recipe: dict[uuid.UUID, list[str]] = {}
    for recipe_id, name in (await db.execute(missing_stmt)).all():
        missing_by_recipe.setdefault(recipe_id, []).append(name)

    matches: list[FridgeMatch] = []
    for row in rows:
        # Stash the computed counts on the ORM object so from_attributes picks
        # them up, mirroring how recipe.macros is attached elsewhere.
        recipe = row.Recipe
        recipe.matched_count = row.matched_count
        recipe.missing_count = row.missing_count
        recipe.total_relevant_count = row.total_relevant_count
        recipe.missing_ingredient_names = sorted(set(missing_by_recipe.get(recipe.id, [])))
        matches.append(FridgeMatch.model_validate(recipe))
    return matches


@router.post("/", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    payload: RecipeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipe = Recipe(
        title=payload.title,
        description=payload.description,
        instructions=payload.instructions,
        image_key=payload.image_key,
        recipie_metadata=payload.recipie_metadata,
        author_id=current_user.id,
    )
    db.add(recipe)
    await db.flush()

    for item in payload.recipe_ingredients:
        ingredient = await _upsert_ingredient(item.ingredient_name, item.food_id, db)
        db.add(RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=item.quantity,
            unit=item.unit,
            note=item.note,
            sort_order=item.sort_order,
        ))

    tags = await _resolve_tags(payload.tag_ids, db)
    if tags:
        await db.execute(
            recipe_tags.insert(),
            [{"recipe_id": recipe.id, "tag_id": tag.id} for tag in tags],
        )

    await db.commit()
    return await _get_recipe_with_relations(recipe.id, db, refresh_macros=True)


# Declared before "/{recipe_id}" so "macros-preview" is never parsed as a UUID.
@router.post("/macros-preview", response_model=MacrosPreview)
async def preview_macros(
    payload: MacrosPreviewRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Compute per-serving macros for a draft (unsaved) recipe.

    Each line's food is the supplied food_id, or a best-effort auto-match on the
    ingredient name. Returns per-line resolution detail so the UI can guide fixes.
    Nothing is persisted.
    """
    # Resolve a food_id per line (given, else auto-matched by name).
    resolved_ids: list[int | None] = []
    for item in payload.recipe_ingredients:
        if item.food_id is not None:
            resolved_ids.append(item.food_id)
        else:
            resolved_ids.append(await _match_food(item.ingredient_name, db))

    wanted = {fid for fid in resolved_ids if fid is not None}
    foods_by_id: dict[int, Food] = {}
    if wanted:
        result = await db.execute(
            select(Food).where(Food.id.in_(wanted)).options(selectinload(Food.portions))
        )
        foods_by_id = {f.id: f for f in result.scalars().all()}

    lines: list[MacroLine] = []
    line_results: list[MacrosLineResult] = []
    for item, fid in zip(payload.recipe_ingredients, resolved_ids):
        food = foods_by_id.get(fid) if fid is not None else None
        lines.append(MacroLine(food=food, quantity=item.quantity, unit=item.unit, name=item.ingredient_name))
        if food is None:
            line_results.append(MacrosLineResult(
                ingredient_name=item.ingredient_name, resolved=False, reason="no_food",
            ))
            continue
        _, reason = resolve_grams(item.quantity, item.unit, food.portions)
        line_results.append(MacrosLineResult(
            ingredient_name=item.ingredient_name,
            resolved=reason is None,
            food_id=food.id,
            food_name=food.name,
            reason=reason,
            supported_units=supported_units(food.portions) if reason == "unit_unmatched" else [],
        ))

    macros = compute_macros(lines, payload.servings or 1.0)
    return MacrosPreview(**asdict(macros), lines=line_results)


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(recipe_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    recipe = await _get_recipe_with_relations(recipe_id, db)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.patch("/{recipe_id}", response_model=RecipeResponse)
async def update_recipe(
    recipe_id: uuid.UUID,
    payload: RecipeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipe = await _get_recipe_with_relations(recipe_id, db)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.author_id is not None and recipe.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the recipe author")

    for schema_field, model_attr in [
        ("title", "title"),
        ("description", "description"),
        ("instructions", "instructions"),
        ("image_key", "image_key"),
        ("recipie_metadata", "recipie_metadata"),
    ]:
        value = getattr(payload, schema_field, None)
        if value is not None:
            setattr(recipe, model_attr, value)

    if payload.recipe_ingredients is not None:
        for ri in list(recipe.recipe_ingredients):
            await db.delete(ri)
        await db.flush()
        for item in payload.recipe_ingredients:
            ingredient = await _upsert_ingredient(item.ingredient_name, item.food_id, db)
            db.add(RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=item.quantity,
                unit=item.unit,
                note=item.note,
                sort_order=item.sort_order,
            ))

    if payload.tag_ids is not None:
        await db.execute(recipe_tags.delete().where(recipe_tags.c.recipe_id == recipe.id))
        tags = await _resolve_tags(payload.tag_ids, db)
        if tags:
            await db.execute(
                recipe_tags.insert(),
                [{"recipe_id": recipe.id, "tag_id": tag.id} for tag in tags],
            )

    await db.commit()
    return await _get_recipe_with_relations(recipe.id, db, refresh_macros=True)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.author_id is not None and recipe.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the recipe author")
    if recipe.image_key:
        await delete_file(recipe.image_key)
    await db.delete(recipe)
    await db.commit()


# --- Recipe image sub-resource ---

@router.post("/{recipe_id}/image", response_model=RecipeResponse)
async def upload_recipe_image(
    recipe_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipe = await _get_recipe_with_relations(recipe_id, db)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.author_id is not None and recipe.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the recipe author")

    data = await file.read()
    try:
        sanitized, content_type = sanitize_image(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    ext = content_type.split("/")[1]  # jpeg, png, or webp
    key = f"images/{recipe_id}/{uuid.uuid4().hex}.{ext}"

    old_key = recipe.image_key
    if old_key:
        await delete_file(old_key)

    await upload_file(key, sanitized, content_type)
    recipe.image_key = key
    await db.commit()

    return await _get_recipe_with_relations(recipe_id, db)


@router.delete("/{recipe_id}/image", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe_image(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.author_id is not None and recipe.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the recipe author")
    if recipe.image_key:
        await delete_file(recipe.image_key)
        recipe.image_key = None
        await db.commit()


@router.get("/{recipe_id}/image-url")
async def get_recipe_image_url(recipe_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if not recipe.image_key:
        raise HTTPException(status_code=404, detail="Recipe has no image")
    return {"url": await get_presigned_url(recipe.image_key)}


# --- Recipe ingredient sub-resource ---

async def _get_recipe_ingredient(recipe_id: uuid.UUID, ri_id: uuid.UUID, db: AsyncSession) -> RecipeIngredient:
    result = await db.execute(
        select(RecipeIngredient)
        .where(RecipeIngredient.recipe_id == recipe_id, RecipeIngredient.id == ri_id)
        .options(selectinload(RecipeIngredient.ingredient))
    )
    ri = result.scalar_one_or_none()
    if not ri:
        raise HTTPException(status_code=404, detail="Recipe ingredient not found")
    return ri


@router.get("/{recipe_id}/ingredients", response_model=list[RecipeIngredientResponse])
async def list_recipe_ingredients(recipe_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    result = await db.execute(
        select(RecipeIngredient)
        .where(RecipeIngredient.recipe_id == recipe_id)
        .options(selectinload(RecipeIngredient.ingredient))
        .order_by(RecipeIngredient.sort_order)
    )
    return result.scalars().all()


@router.post(
    "/{recipe_id}/ingredients",
    response_model=RecipeIngredientResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_recipe_ingredient(
    recipe_id: uuid.UUID,
    payload: RecipeIngredientCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    ingredient = await _upsert_ingredient(payload.ingredient_name, payload.food_id, db)
    ri = RecipeIngredient(
        recipe_id=recipe_id,
        ingredient_id=ingredient.id,
        quantity=payload.quantity,
        unit=payload.unit,
        note=payload.note,
        sort_order=payload.sort_order,
    )
    db.add(ri)
    await db.commit()
    await _get_recipe_with_relations(recipe_id, db, refresh_macros=True)  # rebuild macro cache
    return await _get_recipe_ingredient(recipe_id, ri.id, db)


@router.patch("/{recipe_id}/ingredients/{ri_id}", response_model=RecipeIngredientResponse)
async def update_recipe_ingredient(
    recipe_id: uuid.UUID,
    ri_id: uuid.UUID,
    payload: RecipeIngredientCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ri = await _get_recipe_ingredient(recipe_id, ri_id, db)
    if payload.ingredient_name != ri.ingredient.name or payload.food_id is not None:
        ri.ingredient = await _upsert_ingredient(payload.ingredient_name, payload.food_id, db)
    if payload.quantity is not None:
        ri.quantity = payload.quantity
    if payload.unit is not None:
        ri.unit = payload.unit
    if payload.note is not None:
        ri.note = payload.note
    ri.sort_order = payload.sort_order
    await db.commit()
    await _get_recipe_with_relations(recipe_id, db, refresh_macros=True)  # rebuild macro cache
    return await _get_recipe_ingredient(recipe_id, ri_id, db)


@router.delete("/{recipe_id}/ingredients/{ri_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe_ingredient(
    recipe_id: uuid.UUID,
    ri_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ri = await _get_recipe_ingredient(recipe_id, ri_id, db)
    await db.delete(ri)
    await db.commit()
    await _get_recipe_with_relations(recipe_id, db, refresh_macros=True)  # rebuild macro cache
