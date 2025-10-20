from fastapi import APIRouter, Depends
from src.core.dependecy import get_current_user
from src.modules.subscription_service.src.controllers.subscription_service_controller import SubscriptionServiceController

router = APIRouter(dependencies=[Depends(get_current_user)])
controller = SubscriptionServiceController()

@router.post("/createConfig")
def create_configuration(payload: dict):
    result = controller.create_configuration(payload)
    return {"status": "ok", "result": result}


@router.get("/getConfig/{subscription_id}")
def get_configuration(subscription_id: str):
    result = controller.get_configuration(subscription_id)
    fields = [
        "confidence_response_threshold",
        "confidence_review_mail",
        "priority_threshold",
        "confidence_classification_threshold",
        "urgent_meeting_threshold",
    ]
    if not result:
        return {"status": "not_found"}
    filtered = {k: result.get(k) for k in fields}
    return {"status": "ok", "result": filtered}


@router.patch("/updateConfig/{subscription_id}")
def update_configuration(subscription_id: str, payload: dict):
    updated = controller.update_configuration(subscription_id, payload)
    return {"status": "ok", "result": updated}