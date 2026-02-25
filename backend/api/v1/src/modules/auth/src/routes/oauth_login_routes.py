from fastapi import APIRouter, Request
from fastapi.params import Depends

from src.core.dependecy import get_current_user

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

router = APIRouter(
    tags=["Auth OAuth Login"], 
    dependencies=[Depends(get_current_user)],
)

@router.post("/oauth/login/{provider_name}")
async def oauth_login_route(provider_name: str, request: Request):
    """
    Inizia il processo di autenticazione OAuth per il provider specificato.
    
    IMPORTANTE: è OBBLIGATORIO passare il service_id ottenuto da /create-new-service.
    Senza service_id, la richiesta fallirà.
    """
    try:
        subscription_id = None
        services = None
        email = None
        service_id = None
        
        # Prova prima a leggere come form data
        if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            form_data = await request.form()
            subscription_id = form_data.get("subscription_id")
            services = form_data.get("services", "all")  # default to "all"
            email = form_data.get("email")  # Può essere None
            service_id = form_data.get("service_id")  # ID del service esistente da aggiornare
        else:
            # Prova come JSON
            json_data = await request.json()
            subscription_id = json_data.get("subscription_id")
            services = json_data.get("services", "all")  # default to "all"
            email = json_data.get("email")  # Può essere None
            service_id = json_data.get("service_id")  # ID del service esistente da aggiornare
        
        if not subscription_id:
            raise SubscriptionIdRequiredException()
        
        if not service_id:
            raise BadRequestException(detail="service_id è obbligatorio.")
        
        oauth_request = OAuthLoginRequest(subscription_id=subscription_id, services=services, email=email, service_id=service_id)
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