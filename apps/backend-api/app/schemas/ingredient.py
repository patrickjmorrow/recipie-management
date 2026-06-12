import uuid

from pydantic import BaseModel

from app.schemas.food import FoodSearchResult


class IngredientCreate(BaseModel):
    name: str


class IngredientResponse(BaseModel):
    id: uuid.UUID
    name: str
    food_id: int | None = None
    food_match: str | None = None
    # The linked USDA food (name/category), so the UI can show the match without an extra request.
    food: FoodSearchResult | None = None

    model_config = {"from_attributes": True}


class IngredientFoodUpdate(BaseModel):
    # food_id=None means "no good match exists" -> recorded as 'rejected'.
    food_id: int | None = None


class RecipeIngredientCreate(BaseModel):
    ingredient_name: str
    quantity: float | None = None
    unit: str | None = None
    note: str | None = None
    sort_order: int = 0
    # A non-null food_id confirms the ingredient's USDA food link (overwriting any
    # existing one). Null/omitted leaves the existing link / lets auto-match run.
    food_id: int | None = None


class RecipeIngredientResponse(BaseModel):
    id: uuid.UUID
    ingredient: IngredientResponse
    quantity: float | None
    unit: str | None
    note: str | None
    sort_order: int

    model_config = {"from_attributes": True}
