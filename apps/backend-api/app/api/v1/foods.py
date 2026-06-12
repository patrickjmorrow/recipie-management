from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.food import FoodSearchResult
from app.services.food_search import search_foods

router = APIRouter(prefix="/foods", tags=["foods"])


@router.get("/", response_model=list[FoodSearchResult])
async def search_foods_endpoint(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await search_foods(db, q, limit)
