from fastapi import APIRouter, Request
from ..controllers.oauth_login_controller import (
    oauth_login,
    google_callback,
    microsoft_callback,
    OAuthLoginRequest
)

router = APIRouter()

@router.post("/oauth/login/{provider_name}")
async def oauth_login_route(provider_name: str, oauth_request: OAuthLoginRequest, request: Request):
    """
    Inizia il processo di autenticazione OAuth per il provider specificato.
    
    Args:
        provider_name: Nome del provider OAuth ('google' o 'microsoft')
        oauth_request: Contiene il subscription_id nel body della richiesta
        request: Oggetto FastAPI Request
    
    Returns:
        RedirectResponse alla pagina di autenticazione del provider
    """
    return await oauth_login(provider_name, oauth_request, request)


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