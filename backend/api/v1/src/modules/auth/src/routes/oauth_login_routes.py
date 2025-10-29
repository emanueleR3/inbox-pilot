from fastapi import APIRouter, HTTPException, Request
from ..controllers.oauth_login_controller import (
    oauth_login,
    google_callback,
    microsoft_callback,
    OAuthLoginRequest
)

router = APIRouter()

@router.post("/oauth/login/{provider_name}")
async def oauth_login_route(provider_name: str, request: Request):
    """
    Inizia il processo di autenticazione OAuth per il provider specificato.
    """
    try:
        subscription_id = None
        services = None
        
        # Prova prima a leggere come form data
        if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            form_data = await request.form()
            subscription_id = form_data.get("subscription_id")
            services = form_data.get("services", "all")  # default to "all"
        else:
            # Prova come JSON
            json_data = await request.json()
            subscription_id = json_data.get("subscription_id")
            services = json_data.get("services", "all")  # default to "all"
        
        if not subscription_id:
            raise HTTPException(status_code=400, detail="Missing subscription_id")
        
        oauth_request = OAuthLoginRequest(subscription_id=subscription_id, services=services)
        return await oauth_login(provider_name, oauth_request, request)
        
    except Exception as e:
        import logging
        logger = logging.getLogger("oauth_login_routes")
        
        logger.error(f"Error in OAuth login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during OAuth login")

@router.get("/google/callback")
async def google_callback_route(request: Request):
    """
    Gestisce il callback di Google OAuth dopo l'autenticazione dell'utente.
    """
    return await google_callback(request)

@router.get("/microsoft/callback")
async def microsoft_callback_route(request: Request):
    """
    Gestisce il callback di Microsoft OAuth dopo l'autenticazione dell'utente.
    """
    return await microsoft_callback(request)