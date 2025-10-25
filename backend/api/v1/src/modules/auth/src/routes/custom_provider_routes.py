from fastapi import APIRouter, Depends, Body, HTTPException, status
from src.core.dependecy import get_current_user
from src.modules.auth.src.controllers.custom_provider_controller import CustomProviderController

router = APIRouter(tags=["Auth Custom Provider"])

@router.post("/custom-provider/login")
async def custom_login_route(payload: dict):
    return await CustomProviderController.custom_provider_login(payload)