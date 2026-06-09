from fastapi import APIRouter

from app.api.v1 import recipes

router = APIRouter(prefix="/api/v1")
router.include_router(recipes.router)
