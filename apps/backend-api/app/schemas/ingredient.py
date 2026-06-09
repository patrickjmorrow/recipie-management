import uuid

from pydantic import BaseModel


class IngredientCreate(BaseModel):
    name: str


class IngredientResponse(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class RecipeIngredientCreate(BaseModel):
    ingredient_name: str
    quantity: float | None = None
    unit: str | None = None
    note: str | None = None
    sort_order: int = 0


class RecipeIngredientResponse(BaseModel):
    id: uuid.UUID
    ingredient: IngredientResponse
    quantity: float | None
    unit: str | None
    note: str | None
    sort_order: int

    model_config = {"from_attributes": True}
