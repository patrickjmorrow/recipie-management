import uuid

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import Integer, cast, exists, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ingredient import Ingredient, RecipeIngredient
from app.models.recipe import Recipe
from app.models.tag import Tag, recipe_tags
from app.models.user import User
from app.schemas.ingredient import RecipeIngredientCreate, RecipeIngredientResponse
from app.schemas.recipe import RecipeCreate, RecipeResponse, RecipeSummary, RecipeUpdate
from app.storage.images import sanitize_image
from app.storage.s3 import delete_file, get_presigned_url, upload_file

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
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Recipe)
    filters = []

    if author_id is not None:
        filters.append(Recipe.author_id == author_id)

    if search is not None:
        filters.append(Recipe.title.ilike(f"%{search}%"))

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

    if filters:
        stmt = stmt.where(*filters)

    stmt = stmt.options(selectinload(Recipe.tags))
    stmt = stmt.order_by(Recipe.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
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

    for item in payload.recipe_ingredients:
        ingredient = await _upsert_ingredient(item.ingredient_name, db)
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

    if payload.recipe_ingredients is not None:
        for ri in list(recipe.recipe_ingredients):
            await db.delete(ri)
        await db.flush()
        for item in payload.recipe_ingredients:
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
        await db.execute(recipe_tags.delete().where(recipe_tags.c.recipe_id == recipe.id))
        tags = await _resolve_tags(payload.tag_ids, db)
        if tags:
            await db.execute(
                recipe_tags.insert(),
                [{"recipe_id": recipe.id, "tag_id": tag.id} for tag in tags],
            )

    await db.commit()
    return await _get_recipe_with_relations(recipe.id, db)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(recipe_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
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
