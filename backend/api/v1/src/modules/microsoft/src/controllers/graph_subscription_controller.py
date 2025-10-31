import os
import httpx
from datetime import datetime, timedelta
from src.core.logger import setup_logger

logger = setup_logger()

async def create_subscription_for_user(access_token: str, user_id: str):
    """
    Crea subscription su Microsoft Graph per ricevere notifiche di nuove email.
    Ora crea due subscription: una per Inbox e una per SentItems.
    """
    expiration = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"  # dev: 1h, prod: 3 giorni
    webhook_url = os.getenv("MICROSOFT_WEBHOOK_URL")

    # Subscription per email ricevute (Inbox)
    inbox_subscription_data = {
        "changeType": "created",
        "notificationUrl": webhook_url,
        "resource": f"/users/{user_id}/mailFolders('Inbox')/messages",
        "expirationDateTime": expiration,
        "clientState": "secretClientValue",
    }

    # Subscription per email inviate (SentItems)
    sent_subscription_data = {
        "changeType": "created", 
        "notificationUrl": webhook_url,
        "resource": f"/users/{user_id}/mailFolders('SentItems')/messages",
        "expirationDateTime": expiration,
        "clientState": "secretClientValue",
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    subscriptions = []

    async with httpx.AsyncClient() as client:
        # Crea subscription per Inbox
        try:
            inbox_response = await client.post(
                "https://graph.microsoft.com/v1.0/subscriptions",
                json=inbox_subscription_data,
                headers=headers,
            )

            if inbox_response.status_code not in [200, 201]:
                logger.error(f"Errore creazione subscription Inbox: {inbox_response.status_code}, {inbox_response.text}")
            else:
                inbox_sub = inbox_response.json()
                subscriptions.append({**inbox_sub, "folder_type": "inbox"})
                logger.info(f"Subscription Inbox creata con successo per user {user_id}")
        except Exception as e:
            logger.error(f"Errore creazione subscription Inbox per user {user_id}: {str(e)}")

        # Crea subscription per SentItems
        try:
            sent_response = await client.post(
                "https://graph.microsoft.com/v1.0/subscriptions",
                json=sent_subscription_data,
                headers=headers,
            )

            if sent_response.status_code not in [200, 201]:
                logger.error(f"Errore creazione subscription SentItems: {sent_response.status_code}, {sent_response.text}")
            else:
                sent_sub = sent_response.json()
                subscriptions.append({**sent_sub, "folder_type": "sent"})
                logger.info(f"Subscription SentItems creata con successo per user {user_id}")
        except Exception as e:
            logger.error(f"Errore creazione subscription SentItems per user {user_id}: {str(e)}")

    if not subscriptions:
        raise Exception("Impossibile creare nessuna subscription per l'utente")

    logger.info(f"Create {len(subscriptions)} subscription(s) per user {user_id}")
    return subscriptions