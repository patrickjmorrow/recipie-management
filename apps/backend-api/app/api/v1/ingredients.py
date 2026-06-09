import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ingredient import Ingredient, RecipeIngredient
from app.models.user import User
from app.schemas.ingredient import IngredientCreate, IngredientResponse

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("/", response_model=list[IngredientResponse])
async def list_ingredients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ingredient).order_by(Ingredient.name))
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
