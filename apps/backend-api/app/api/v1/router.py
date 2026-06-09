from fastapi import APIRouter

from app.api.v1 import auth, ingredients, recipes, tags, users

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(tags.router)
router.include_router(ingredients.router)
router.include_router(recipes.router)
