from fastapi import APIRouter
from .subscription_route import router as subscription_router
from .settings_subscription import router as settings_subscription_router

router = APIRouter()
router.include_router(subscription_router)
router.include_router(settings_subscription_router)