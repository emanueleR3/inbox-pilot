import os
import httpx
from datetime import datetime, timedelta
from src.core.logger import setup_logger

logger = setup_logger()

async def create_subscription_for_user(access_token: str, user_id: str):
    """
    Crea una subscription su Microsoft Graph per ricevere notifiche di nuove email.
    """
    expiration = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"  # dev: 1h, prod: 3 giorni
    webhook_url = os.getenv("MICROSOFT_WEBHOOK_URL")

    subscription_data = {
        "changeType": "created",
        "notificationUrl": webhook_url,
        "resource": f"/users/{user_id}/mailFolders('Inbox')/messages",
        "expirationDateTime": expiration,
        "clientState": "secretClientValue",
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://graph.microsoft.com/v1.0/subscriptions",
            json=subscription_data,
            headers=headers,
        )

        if response.status_code not in [200, 201]:
            logger.error(f"Errore creazione subscription: {response.status_code}, {response.text}")
            raise Exception(f"Errore creazione subscription: {response.text}")

        logger.info(f"Subscription creata con successo per user {user_id}")
        return response.json()