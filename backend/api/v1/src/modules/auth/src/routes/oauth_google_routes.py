from fastapi import APIRouter, Request
from src.modules.auth.src.controllers.oauth_google_controller import (
    google_login,
    google_callback
)

router = APIRouter()

@router.get("/google/login")
async def google_login_route():
    return await google_login()

@router.get("/google/callback")
async def google_callback_route(request: Request):
    return await google_callback(request)