from fastapi import APIRouter
from .subscription_service_route import router as subscription_service_router
from .settings_sub_settings_route import router as settings_sub_settings_router

router = APIRouter()
router.include_router(subscription_service_router)
router.include_router(settings_sub_settings_router)