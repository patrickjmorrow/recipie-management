import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ingredient import Ingredient, RecipeIngredient
from app.models.recipe import Recipe
from app.models.tag import Tag
from app.models.user import User
from app.schemas.ingredient import RecipeIngredientCreate, RecipeIngredientResponse
from app.schemas.recipe import RecipeCreate, RecipeResponse, RecipeSummary, RecipeUpdate

router = APIRouter(prefix="/recipes", tags=["recipes"])


async def _get_recipe_with_relations(recipe_id: uuid.UUID, db: AsyncSession) -> Recipe | None:
    result = await db.execute(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.tags),
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient),
        )
    )
    return result.scalar_one_or_none()


async def _upsert_ingredient(name: str, db: AsyncSession) -> Ingredient:
    result = await db.execute(select(Ingredient).where(Ingredient.name == name))
    ingredient = result.scalar_one_or_none()
    if ingredient is None:
        ingredient = Ingredient(name=name)
        db.add(ingredient)
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
async def list_recipes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Recipe).order_by(Recipe.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe(payload: RecipeCreate, db: AsyncSession = Depends(get_db)):
    recipe = Recipe(
        title=payload.title,
        description=payload.description,
        instructions=payload.instructions,
        image_key=payload.image_key,
        recipie_metadata=payload.recipie_metadata,
    )
    db.add(recipe)
    await db.flush()

    for item in payload.ingredients:
        ingredient = await _upsert_ingredient(item.ingredient_name, db)
        db.add(RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=item.quantity,
            unit=item.unit,
            note=item.note,
            sort_order=item.sort_order,
        ))

    for tag in await _resolve_tags(payload.tag_ids, db):
        recipe.tags.append(tag)

    await db.commit()
    return await _get_recipe_with_relations(recipe.id, db)


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(recipe_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    recipe = await _get_recipe_with_relations(recipe_id, db)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.patch("/{recipe_id}", response_model=RecipeResponse)
async def update_recipe(recipe_id: uuid.UUID, payload: RecipeUpdate, db: AsyncSession = Depends(get_db)):
    recipe = await _get_recipe_with_relations(recipe_id, db)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

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

    if payload.ingredients is not None:
        for ri in list(recipe.recipe_ingredients):
            await db.delete(ri)
        await db.flush()
        for item in payload.ingredients:
            ingredient = await _upsert_ingredient(item.ingredient_name, db)
            db.add(RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=item.quantity,
                unit=item.unit,
                note=item.note,
                sort_order=item.sort_order,
            ))

    if payload.tag_ids is not None:
        recipe.tags.clear()
        for tag in await _resolve_tags(payload.tag_ids, db):
            recipe.tags.append(tag)

    await db.commit()
    return await _get_recipe_with_relations(recipe.id, db)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(recipe_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    await db.delete(recipe)
    await db.commit()


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
    ingredient = await _upsert_ingredient(payload.ingredient_name, db)
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
    if payload.ingredient_name != ri.ingredient.name:
        ri.ingredient = await _upsert_ingredient(payload.ingredient_name, db)
    if payload.quantity is not None:
        ri.quantity = payload.quantity
    if payload.unit is not None:
        ri.unit = payload.unit
    if payload.note is not None:
        ri.note = payload.note
    ri.sort_order = payload.sort_order
    await db.commit()
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
