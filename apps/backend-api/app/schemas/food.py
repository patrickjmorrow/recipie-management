import uuid

from pydantic import BaseModel


class FoodSearchResult(BaseModel):
    id: int
    name: str
    category: str | None = None

    model_config = {"from_attributes": True}


class IngredientFoodLink(BaseModel):
    ingredient_id: uuid.UUID
    # food_id=None means "no good match exists" -> recorded as 'rejected'.
    food_id: int | None = None


class BulkIngredientFoodUpdate(BaseModel):
    links: list[IngredientFoodLink]
