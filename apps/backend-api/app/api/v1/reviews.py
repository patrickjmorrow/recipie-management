import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.recipe import Recipe
from app.models.review import RecipeReview
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate

router = APIRouter(prefix="/recipes/{recipe_id}/reviews", tags=["reviews"])


async def _get_recipe_or_404(recipe_id: uuid.UUID, db: AsyncSession) -> Recipe:
    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


async def _get_review_or_404(review_id: uuid.UUID, recipe_id: uuid.UUID, db: AsyncSession) -> RecipeReview:
    result = await db.execute(
        select(RecipeReview).where(
            RecipeReview.id == review_id,
            RecipeReview.recipe_id == recipe_id,
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


async def _get_review_with_reviewer(review_id: uuid.UUID, recipe_id: uuid.UUID, db: AsyncSession) -> RecipeReview:
    result = await db.execute(
        select(RecipeReview)
        .where(RecipeReview.id == review_id, RecipeReview.recipe_id == recipe_id)
        .options(selectinload(RecipeReview.reviewer))
    )
    return result.scalar_one()


def _to_response(review: RecipeReview) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        recipe_id=review.recipe_id,
        reviewer_id=review.reviewer_id,
        reviewer_display_name=review.reviewer.display_name if review.reviewer else None,
        rating=review.rating,
        body=review.body,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


async def _refresh_aggregates(recipe_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(func.avg(RecipeReview.rating), func.count()).where(
            RecipeReview.recipe_id == recipe_id
        )
    )
    avg, count = result.one()
    await db.execute(
        update(Recipe)
        .where(Recipe.id == recipe_id)
        .values(avg_rating=avg, review_count=count or 0)
    )


@router.get("/", response_model=list[ReviewResponse])
async def list_reviews(
    recipe_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    await _get_recipe_or_404(recipe_id, db)
    result = await db.execute(
        select(RecipeReview)
        .where(RecipeReview.recipe_id == recipe_id)
        .options(selectinload(RecipeReview.reviewer))
        .order_by(RecipeReview.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_to_response(r) for r in result.scalars().all()]


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    recipe_id: uuid.UUID,
    payload: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipe = await _get_recipe_or_404(recipe_id, db)
    if recipe.author_id == current_user.id:
        raise HTTPException(status_code=403, detail="Authors cannot review their own recipes")

    existing = await db.execute(
        select(RecipeReview).where(
            RecipeReview.recipe_id == recipe_id,
            RecipeReview.reviewer_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already reviewed this recipe")

    review = RecipeReview(
        recipe_id=recipe_id,
        reviewer_id=current_user.id,
        rating=payload.rating,
        body=payload.body,
    )
    db.add(review)
    await db.flush()
    await _refresh_aggregates(recipe_id, db)
    await db.commit()
    return _to_response(await _get_review_with_reviewer(review.id, recipe_id, db))


@router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review(
    recipe_id: uuid.UUID,
    review_id: uuid.UUID,
    payload: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = await _get_review_or_404(review_id, recipe_id, db)
    if review.reviewer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your review")

    if payload.rating is not None:
        review.rating = payload.rating
    if payload.body is not None:
        review.body = payload.body

    await db.flush()
    await _refresh_aggregates(recipe_id, db)
    await db.commit()
    return _to_response(await _get_review_with_reviewer(review.id, recipe_id, db))


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    recipe_id: uuid.UUID,
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = await _get_review_or_404(review_id, recipe_id, db)
    if review.reviewer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your review")

    await db.delete(review)
    await db.flush()
    await _refresh_aggregates(recipe_id, db)
    await db.commit()
