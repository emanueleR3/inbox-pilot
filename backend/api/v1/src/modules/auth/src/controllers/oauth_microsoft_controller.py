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
subscription_service_dao = SubscriptionServiceDAO()


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
        # Log completo della richiesta per debug
        logger.info(f"Microsoft callback URL: {request.url}")
        logger.info(f"Query params: {dict(request.query_params)}")
        
        # Controlla se c'è un errore da Microsoft
        error = request.query_params.get("error")
        error_description = request.query_params.get("error_description")
        
        if error:
            logger.error(f"Microsoft OAuth error: {error}")
            logger.error(f"Error description: {error_description}")
            raise HTTPException(status_code=400, detail=f"Microsoft OAuth error: {error} - {error_description}")
        
        code = request.query_params.get("code")
        if not code:
            logger.error("No authorization code in callback")
            raise HTTPException(status_code=400, detail="Missing authorization code")

        logger.info(f"Authorization code received: {code[:20]}...")

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

        result = subscription_service_dao.save_microsoft_credentials(
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