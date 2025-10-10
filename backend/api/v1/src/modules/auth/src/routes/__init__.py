from fastapi import APIRouter
from src.modules.auth.src.routes.oauth_google_routes import router as google_router
from src.modules.auth.src.routes.oauth_microsoft_routes import router as microsoft_router

router = APIRouter()
router.include_router(google_router)
router.include_router(microsoft_router)