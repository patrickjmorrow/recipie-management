import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.ingredient import RecipeIngredientCreate, RecipeIngredientResponse
from app.schemas.tag import TagResponse


class RecipeCreate(BaseModel):
    title: str
    description: str | None = None
    instructions: str | None = None
    image_key: str | None = None
    recipie_metadata: dict[str, Any] | None = None
    recipe_ingredients: list[RecipeIngredientCreate] = []
    tag_ids: list[uuid.UUID] = []


class RecipeUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    instructions: str | None = None
    image_key: str | None = None
    recipie_metadata: dict[str, Any] | None = None
    recipe_ingredients: list[RecipeIngredientCreate] | None = None
    tag_ids: list[uuid.UUID] | None = None


class RecipeSummary(BaseModel):
    """Lightweight view used in list endpoints — no ingredients or instructions."""

    id: uuid.UUID
    author_id: uuid.UUID | None
    title: str
    description: str | None
    image_key: str | None
    recipie_metadata: dict[str, Any] | None
    tags: list[TagResponse] = []
    avg_rating: float | None = None
    review_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FridgeMatch(RecipeSummary):
    """A recipe ranked for "what's in my fridge": summary plus how well it's covered.

    Counts ignore pantry staples (salt, pepper, common spices) — those are
    assumed on-hand, so `missing_count` reflects only ingredients worth a shop.
    """

    matched_count: int
    missing_count: int
    total_relevant_count: int
    missing_ingredient_names: list[str] = []


class RecipeMacros(BaseModel):
    """Per-serving nutrition computed from linked USDA foods.

    `unresolved` lists ingredients excluded from the totals (no food link or no
    convertible unit) so the numbers are never silently understated.
    """

    energy_kcal: float
    protein_g: float
    fat_g: float
    sat_fat_g: float
    carbs_g: float
    fiber_g: float
    sugar_g: float
    sodium_mg: float
    servings: float
    unresolved: list[str] = []

    model_config = {"from_attributes": True}


class MacrosPreviewLine(BaseModel):
    ingredient_name: str
    quantity: float | None = None
    unit: str | None = None
    food_id: int | None = None


class MacrosPreviewRequest(BaseModel):
    """A draft recipe's ingredient lines for computing macros without saving."""

    servings: float | None = None
    recipe_ingredients: list[MacrosPreviewLine] = []


class MacrosLineResult(BaseModel):
    """Per-line resolution detail for a draft preview, so the UI can guide fixes."""

    ingredient_name: str
    resolved: bool
    food_id: int | None = None
    food_name: str | None = None
    # None when resolved; else 'no_food' | 'no_quantity' | 'no_unit' | 'unit_unmatched'.
    reason: str | None = None
    # Volume/count units this food supports (for 'unit_unmatched'); mass units always work.
    supported_units: list[str] = []


class MacrosPreview(RecipeMacros):
    """Draft macros plus per-line resolution detail."""

    lines: list[MacrosLineResult] = []


class RecipeResponse(BaseModel):
    """Full recipe detail including nested ingredients and tags."""

    id: uuid.UUID
    author_id: uuid.UUID | None
    title: str
    description: str | None
    instructions: str | None
    image_key: str | None
    recipie_metadata: dict[str, Any] | None
    recipe_ingredients: list[RecipeIngredientResponse] = []
    tags: list[TagResponse] = []
    macros: RecipeMacros | None = None
    avg_rating: float | None = None
    review_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Keep old name as alias so any existing references don't break during migration
RecipeRead = RecipeResponse


class BrowseSection(BaseModel):
    """One curated landing-page section: a titled row of recipe cards."""

    key: str
    title: str
    subtitle: str | None = None
    recipes: list[RecipeSummary] = []


class BrowseSectionsResponse(BaseModel):
    sections: list[BrowseSection] = []
