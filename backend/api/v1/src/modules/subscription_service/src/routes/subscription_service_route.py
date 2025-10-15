from fastapi import APIRouter
from src.core.database import get_supabase_client
from src.modules.subscription_service.src.controllers.subscription_service_controller import SubscriptionServiceController

router = APIRouter()
controller = SubscriptionServiceController()

@router.post("/createConfig")
def create_configuration(payload: dict):
    result = controller.create_configuration(payload)
    return {"status": "ok", "result": result}