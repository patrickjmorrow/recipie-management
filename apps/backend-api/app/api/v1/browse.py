from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.recipe import BrowseSection, BrowseSectionsResponse
from app.services.browse_sections import build_sections

router = APIRouter(prefix="/browse", tags=["browse"])


@router.get("/sections", response_model=BrowseSectionsResponse)
async def get_browse_sections(
    count: int = Query(default=5, ge=1, le=8),
    card_limit: int = Query(default=12, ge=4, le=24),
    db: AsyncSession = Depends(get_db),
):
    """A randomized subset of curated sections for the landing page.

    The selection (and order within each section) varies per request, so the page
    presents something different each time it loads.
    """
    sections = await build_sections(db, count, card_limit)
    return BrowseSectionsResponse(
        sections=[
            BrowseSection(key=sd.key, title=sd.title, subtitle=sd.subtitle, recipes=recipes)
            for sd, recipes in sections
        ]
    )
