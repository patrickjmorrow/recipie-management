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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Keep old name as alias so any existing references don't break during migration
RecipeRead = RecipeResponse
