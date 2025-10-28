'''
from fastapi import APIRouter, Request
from src.modules.auth.src.controllers.oauth_microsoft_controller import (
    microsoft_login,
    microsoft_callback
)

router = APIRouter()

@router.get("/microsoft/login")
async def microsoft_login_route():
    return await microsoft_login()

@router.get("/microsoft/callback")
async def microsoft_callback_route(request: Request):
    return await microsoft_callback(request)
'''