"""
Notification Router - Handles notification webhook endpoints.
"""

import logging
from fastapi import APIRouter

from ..models.models import NotificationRequest, NotificationResponse
from ..controllers.notification_controller import NotificationController

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/notification",
    tags=["notification"]
)

controller = NotificationController()


@router.post("/send", response_model=NotificationResponse)
async def send_notification(notification: NotificationRequest):
    """
    Webhook endpoint to receive notification requests from automations service.
    
    Args:
        notification: NotificationRequest containing all notification details
        
    Returns:
        NotificationResponse with success status and message
    """
    return controller.send_notification(notification.dict())
