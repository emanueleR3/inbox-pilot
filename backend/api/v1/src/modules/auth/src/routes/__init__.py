from fastapi import APIRouter
from .oauth_google_routes import router as google_router
from .oauth_microsoft_routes import router as microsoft_router
from .user_routes import router as user_router

router = APIRouter()
router.include_router(google_router)
router.include_router(microsoft_router)
router.include_router(user_router)