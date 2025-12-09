import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status

from ..controllers.send_email_controller import SendEmailController

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/send-email",
    tags=["send-email"]
)

controller = SendEmailController()

@router.post("/send-gmail")
async def send_gmail_email(req: dict):
    return controller.send_email_gmail(req)

@router.post("/send-microsoft")
async def send_microsoft_email(req: dict):
    return controller.send_email_microsoft(req)

@router.post("/send-smtp")
async def send_smtp_email(req: dict):
    print("[DEBUG-SENDER] send_smtp_email")
    return controller.send_email_smtp(req)