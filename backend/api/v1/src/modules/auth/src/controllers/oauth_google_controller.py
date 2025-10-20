from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from src.modules.auth.src.utils.google_oauth_client import create_google_flow
from src.core.logger import setup_logger
from src.modules.google.src.controllers.gmail_watch_controller import create_watch_for_user
from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO

import requests

logger = setup_logger()


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
        state = request.cookies.get("oauth_state")
        flow = create_google_flow()
        flow.fetch_token(authorization_response=str(request.url))

        credentials = flow.credentials

        # Recupera info utente dal token
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"}
        ).json()

        logger.info(f"Authenticated Google user: {user_info}")

        # TODO recuperare la subscription_id che si sta gestendo
        subscription_id = "TODO_SUBSCRIPTION_ID"

        # Salva le credenziali nel database
        email = user_info["email"]
        access_token = credentials.token
        refresh_token = credentials.refresh_token
        expiry = credentials.expiry

        result = SubscriptionServiceDAO.save_google_credentials(email, subscription_id, access_token, refresh_token, expiry)
        if result is False:
            logger.error("Errore nel salvataggio delle credenziali Google")
            raise HTTPException(status_code=500, detail="Errore nel salvataggio delle credenziali Google")

        # Crea la watch Gmail
        response = create_watch_for_user(email)
        
        # Salva history_id della watch Gmail
        history_id = response.get("historyId")
        result = SubscriptionServiceDAO.update_history_id(email, history_id)

        token_data = {
            "email": user_info["email"],
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expiry": str(credentials.expiry)
        }

        return JSONResponse({
            "message": "Google account connesso con successo!",
            "user": token_data
        })

    except Exception as e:
        logger.error(f"Errore nel callback Google: {e}")
        raise HTTPException(status_code=400, detail="Errore autenticazione Google")