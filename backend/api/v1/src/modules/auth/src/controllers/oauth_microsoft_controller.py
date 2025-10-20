from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from src.core.logger import setup_logger
from src.modules.auth.src.utils.microsoft_oauth_client import (
    create_microsoft_auth_url,
    exchange_code_for_tokens
)
from src.modules.microsoft.src.controllers.graph_subscription_controller import (
    create_subscription_for_user
)
from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO

import httpx

logger = setup_logger()


async def microsoft_login():
    """
    Reindirizza l'utente alla pagina di consenso Microsoft.
    """
    authorization_url = create_microsoft_auth_url()
    logger.info(f"Redirecting to Microsoft OAuth: {authorization_url}")
    return RedirectResponse(url=authorization_url)


async def microsoft_callback(request: Request):
    """
    Gestisce il callback dopo il login Microsoft.
    """
    try:
        code = request.query_params.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")

        # 1️⃣ Scambio del codice con i token
        tokens = await exchange_code_for_tokens(code)
        access_token = tokens.get("access_token")

        logger.info("Microsoft tokens retrieved successfully")

        # 2️⃣ Recupera informazioni sull’utente
        async with httpx.AsyncClient() as client:
            user_info_response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()

        email = user_info.get("userPrincipalName")
        user_id = user_info.get("id")
        refresh_token = tokens.get("refresh_token")
        expiry = tokens.get("expires_in")

        logger.info(f"Authenticated Microsoft user: {email}")

        # 3️⃣ Crea la subscription per ricevere notifiche email 
        subscription = await create_subscription_for_user(access_token, user_id)

        logger.info(f"Microsoft subscription created for {email}: {subscription.get('id')}")

        #TODO recuperare la subscription_id che si sta gestendo
        subscription_id = "TODO_SUBSCRIPTION_ID"

        result = SubscriptionServiceDAO.save_microsoft_credentials(
            email, 
            subscription_id,
            access_token,
            refresh_token,
            expiry,
            subscription.get("id"),
            subscription.get("expirationDateTime")
        )

        if result is False:
            logger.error("Errore nel salvataggio delle credenziali Microsoft")
            raise HTTPException(status_code=500, detail="Errore nel salvataggio delle credenziali Microsoft")


        token_data = {
            "email": email,
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expiry": tokens.get("expires_in"),
        }

        return JSONResponse({
            "message": "Microsoft account connesso con successo!",
            "user": token_data,
            "subscription": subscription
        })

    except Exception as e:
        logger.error(f"Errore nel callback Microsoft: {e}")
        raise HTTPException(status_code=400, detail=f"Errore autenticazione Microsoft: {e}")