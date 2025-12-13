from fastapi import APIRouter, Request
from ..controllers.oauth_login_controller import (
    oauth_login,
    google_callback,
    microsoft_callback,
    OAuthLoginRequest
)
from src.handler_exception import (
    SubscriptionIdRequiredException,
    OAuthException,
    BadRequestException
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
        email = None
        
        # Prova prima a leggere come form data
        if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            form_data = await request.form()
            subscription_id = form_data.get("subscription_id")
            services = form_data.get("services", "all")  # default to "all"
            email = form_data.get("email")  # Può essere None
        else:
            # Prova come JSON
            json_data = await request.json()
            subscription_id = json_data.get("subscription_id")
            services = json_data.get("services", "all")  # default to "all"
            email = json_data.get("email")  # Può essere None
        
        if not subscription_id:
            raise SubscriptionIdRequiredException()
        
        oauth_request = OAuthLoginRequest(subscription_id=subscription_id, services=services, email=email)
        return await oauth_login(provider_name, oauth_request, request)
        
    except SubscriptionIdRequiredException:
        raise
    except BadRequestException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger("oauth_login_routes")
        logger.error(f"Error in OAuth login: {e}")
        raise OAuthException(provider=provider_name, reason=str(e))

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