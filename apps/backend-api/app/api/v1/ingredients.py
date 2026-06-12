import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.food import Food
from app.models.ingredient import Ingredient, RecipeIngredient
from app.models.user import User
from app.schemas.food import BulkIngredientFoodUpdate, FoodSearchResult
from app.schemas.ingredient import IngredientCreate, IngredientFoodUpdate, IngredientResponse
from app.services.food_search import search_foods

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


async def _apply_food_link(ingredient: Ingredient, food_id: int | None, db: AsyncSession) -> None:
    """Set or clear an ingredient's USDA food link.

    A non-null food_id marks the link 'confirmed'; clearing it marks 'rejected'.
    Raises 404 if the food_id does not exist.
    """
    if food_id is not None:
        food = await db.get(Food, food_id)
        if not food:
            raise HTTPException(status_code=404, detail="Food not found")
        ingredient.food_id = food_id
        ingredient.food_match = "confirmed"
    else:
        ingredient.food_id = None
        ingredient.food_match = "rejected"


@router.get("/", response_model=list[IngredientResponse])
async def list_ingredients(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List ingredients, optionally filtered by a name substring (for type-ahead)."""
    stmt = select(Ingredient)
    if q is not None and q.strip():
        stmt = stmt.where(Ingredient.name.ilike(f"%{q.strip()}%"))
    stmt = stmt.order_by(Ingredient.name).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
async def create_ingredient(
    payload: IngredientCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ingredient = Ingredient(name=payload.name)
    db.add(ingredient)
    await db.commit()
    await db.refresh(ingredient)
    return ingredient


# Declared before the "/{ingredient_id}" routes so "food" is never parsed as a UUID.
@router.patch("/food", response_model=list[IngredientResponse])
async def bulk_set_ingredient_food(
    payload: BulkIngredientFoodUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Pair (or clear) USDA food links for many ingredients in one call.

    Each link follows the same semantics as PATCH /{ingredient_id}/food:
    a food_id marks the link 'confirmed', a null food_id marks it 'rejected'.
    The whole batch is validated before anything is committed.
    """
    ingredients: list[Ingredient] = []
    for link in payload.links:
        ingredient = await db.get(Ingredient, link.ingredient_id)
        if not ingredient:
            raise HTTPException(status_code=404, detail=f"Ingredient {link.ingredient_id} not found")
        await _apply_food_link(ingredient, link.food_id, db)
        ingredients.append(ingredient)

    await db.commit()
    for ingredient in ingredients:
        await db.refresh(ingredient)
    return ingredients


@router.patch("/{ingredient_id}", response_model=IngredientResponse)
async def update_ingredient(
    ingredient_id: uuid.UUID,
    payload: IngredientCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ingredient = await db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    ingredient.name = payload.name
    await db.commit()
    await db.refresh(ingredient)
    return ingredient


@router.patch("/{ingredient_id}/food", response_model=IngredientResponse)
async def set_ingredient_food(
    ingredient_id: uuid.UUID,
    payload: IngredientFoodUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Confirm or correct the USDA food linked to an ingredient.

    Setting a food_id marks the link 'confirmed'; clearing it marks 'rejected'.
    Either way the backfill auto-matcher will leave it alone afterwards.
    """
    ingredient = await db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    await _apply_food_link(ingredient, payload.food_id, db)

    await db.commit()
    await db.refresh(ingredient)
    return ingredient


@router.get("/{ingredient_id}/food-candidates", response_model=list[FoodSearchResult])
async def list_ingredient_food_candidates(
    ingredient_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Suggest USDA foods to pair with an ingredient, seeded from its name."""
    ingredient = await db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return await search_foods(db, ingredient.name, limit)


@router.post("/{ingredient_id}/food/confirm", response_model=IngredientResponse)
async def confirm_ingredient_food(
    ingredient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Approve an ingredient's existing (auto-matched) food link as-is.

    Promotes the link to 'confirmed' so the backfill auto-matcher leaves it alone.
    """
    ingredient = await db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    if ingredient.food_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ingredient has no food link to confirm.",
        )
    ingredient.food_match = "confirmed"
    await db.commit()
    await db.refresh(ingredient)
    return ingredient


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ingredient(
    ingredient_id: uuid.UUID,
    replacement_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ingredient = await db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    result = await db.execute(
        select(RecipeIngredient).where(RecipeIngredient.ingredient_id == ingredient_id).limit(1)
    )
    in_use = result.scalar_one_or_none() is not None

    if in_use:
        if replacement_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This ingredient is used in recipes. Provide replacement_id to replace it before deleting.",
            )
        replacement = await db.get(Ingredient, replacement_id)
        if not replacement:
            raise HTTPException(status_code=404, detail="Replacement ingredient not found")

        await db.execute(
            update(RecipeIngredient)
            .where(RecipeIngredient.ingredient_id == ingredient_id)
            .values(ingredient_id=replacement_id)
        )

    await db.delete(ingredient)
    await db.commit()
