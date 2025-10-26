from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from src.modules.auth.src.utils.google_oauth_client import create_google_flow
from src.core.logger import setup_logger
from src.modules.google.src.controllers.gmail_watch_controller import create_watch_for_user
from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO
import os

import requests

# Assicurati che la variabile sia impostata anche qui
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

logger = setup_logger()
subscription_service_dao = SubscriptionServiceDAO()

async def google_login():
    """
    Reindirizza l'utente alla pagina di consenso Google.
    """
    flow = create_google_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",      # per ottenere anche il refresh token
        include_granted_scopes="true",
        prompt="consent"            # forza Google a chiedere il consenso anche se già loggato
    )

    logger.info(f"Redirecting to Google OAuth: {authorization_url}")
    response = RedirectResponse(url=authorization_url)
    response.set_cookie(key="oauth_state", value=state, httponly=True)
    return response


async def google_callback(request: Request):
    """
    Gestisce il callback dopo il login Google.
    """
    try:
        # Assicurati che la variabile sia impostata prima di qualsiasi operazione OAuth
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        logger.info(f"OAUTHLIB_INSECURE_TRANSPORT at callback start: {os.environ.get('OAUTHLIB_INSECURE_TRANSPORT')}")
        
        state = request.cookies.get("oauth_state")
        flow = create_google_flow()
        
        # Costruisci l'URL di callback con lo scheme HTTPS per il reverse proxy
        callback_url = str(request.url)
        if callback_url.startswith("http://") and "X-Forwarded-Proto" in request.headers:
            callback_url = callback_url.replace("http://", "https://", 1)
        
        logger.info(f"Processing Google callback with URL: {callback_url}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request scheme: {request.url.scheme}")
        logger.info(f"OAUTHLIB_INSECURE_TRANSPORT before fetch_token: {os.environ.get('OAUTHLIB_INSECURE_TRANSPORT')}")
        
        flow.fetch_token(authorization_response=callback_url)

        credentials = flow.credentials

        # Log degli scope per debug
        if hasattr(credentials, 'scopes'):
            logger.info(f"Granted scopes: {credentials.scopes}")
        else:
            logger.warning("No scopes information available in credentials")

        # Verifica che il token sia valido testando una chiamata API
        try:
            user_info_response = requests.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"}
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch user info: {e}")
            raise HTTPException(status_code=400, detail="Invalid Google token")

        logger.info(f"Authenticated Google user: {user_info}")
        
        # Get email from user_info first
        email = user_info["email"]

        # TODO recuperare la subscription_id che si sta gestendo
        subscription_id = ""
        if email == "dev1@example.com":
            subscription_id = "104216c2-2086-4136-9b18-745c5e682ee4"    # HARDCODED PER ORA 
        elif email == "dev3@example.com":
            subscription_id = "05fd6e28-ba5a-44cf-9fe6-027f0f3b94a8"
        elif email == "dev2@example.com":
            subscription_id = "9a6f91f7-6ea6-466d-b091-9652a117fd34"
        elif email == "contact.outlook@example.com":
            subscription_id = "8bb90df3-d906-46cd-935d-3a377da546a6"
        else:
            logger.warning(f"No subscription_id configured for email: {email}")
            raise HTTPException(status_code=400, detail="Email non autorizzato")

        # Verifica che abbiamo tutti i dati necessari
        if not credentials.token:
            raise HTTPException(status_code=400, detail="Access token mancante")
        
        if not credentials.refresh_token:
            logger.warning("Refresh token mancante - potrebbe essere necessario revocare e riautorizzare")

        # Salva le credenziali nel database
        access_token = credentials.token
        refresh_token = credentials.refresh_token
        expiry = credentials.expiry

        logger.info(f"Saving credentials for {email} - Access token: {access_token[:20]}...")

        # Crea la watch Gmail con gestione errori migliorata
        try:
            logger.info(f"Creating Gmail watch for {email}")
            response = create_watch_for_user(access_token=access_token, refresh_token=refresh_token, email=email)
            logger.info(f"Gmail watch response: {response}")
            
            # Salva history_id della watch Gmail
            history_id = response.get("historyId")
            if not history_id:
                logger.warning(f"No historyId received from Gmail watch response for {email}")
                
        except Exception as watch_error:
            logger.error(f"Failed to create Gmail watch for {email}: {watch_error}")
            # Non blocchiamo l'autenticazione per questo errore, ma lo logghiamo
            logger.warning("Continuing authentication process despite watch creation failure")
        
        try:
            result = subscription_service_dao.save_google_credentials(email, subscription_id, access_token, refresh_token, expiry, history_id)
            if result is False:
                logger.error("Errore nel salvataggio delle credenziali Google nel database")
                raise HTTPException(status_code=500, detail="Errore nel salvataggio delle credenziali Google")
            logger.info(f"Credentials saved successfully for {email}")
        except Exception as save_error:
            logger.error(f"Database error saving credentials: {save_error}")
            raise HTTPException(status_code=500, detail="Errore database nel salvataggio credenziali")

        token_data = {
            "email": user_info["email"],
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expiry": str(credentials.expiry) if credentials.expiry else None
        }

        logger.info(f"Google authentication completed successfully for {email}")
        return JSONResponse({
            "message": "Google account connesso con successo!",
            "user": token_data
        })

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.error(f"Errore nel callback Google: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Errore autenticazione Google")