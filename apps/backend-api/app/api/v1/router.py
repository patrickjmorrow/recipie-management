from fastapi import APIRouter

from app.api.v1 import auth, foods, ingredients, recipes, reviews, tags, users

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(tags.router)
router.include_router(ingredients.router)
router.include_router(foods.router)
router.include_router(recipes.router)
router.include_router(reviews.router)
