from fastapi import APIRouter
from .subscription_service_route import router as subscription_service_router

router = APIRouter()
router.include_router(subscription_service_router)
