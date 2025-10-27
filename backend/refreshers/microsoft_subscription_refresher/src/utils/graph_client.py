import httpx
from datetime import datetime, timedelta
from src.utils.logger import Logger

GRAPH_URL = "https://graph.microsoft.com/v1.0/subscriptions"

async def renew_subscription(access_token: str, subscription_id: str):
    """
    Rinnova una subscription Microsoft Graph per un altro periodo.
    """
    new_expiration = (datetime.utcnow() + timedelta(days=2)).isoformat() + "Z"

    data = {
        "expirationDateTime": new_expiration
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    Logger.log_info(f"### MICROSOFT SUBSCRIPTION 📡 Invio richiesta di rinnovo a Microsoft Graph per subscription: {subscription_id}")
    Logger.log_info(f"### MICROSOFT SUBSCRIPTION 📅 Nuova data di scadenza impostata: {new_expiration}")

    async with httpx.AsyncClient() as client:
        resp = await client.patch(f"{GRAPH_URL}/{subscription_id}", json=data, headers=headers)
        
        Logger.log_info(f"### MICROSOFT SUBSCRIPTION 📨 Risposta da Microsoft Graph: {resp.status_code}")
        
        if resp.status_code not in [200, 202]:
            Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore HTTP {resp.status_code} dal Graph API")
            Logger.log_error(f"### MICROSOFT SUBSCRIPTION 📄 Dettagli errore: {resp.text}")
            raise Exception(f"Errore nel rinnovo subscription {subscription_id}: {resp.status_code}, {resp.text}")
        
        Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ Richiesta di rinnovo completata con successo")
        return resp.json()