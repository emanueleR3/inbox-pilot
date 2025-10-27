# refreshers/microsoft_subscription_refresher/src/subscription_refresher.py
from src.utils.graph_client import renew_subscription
from src.db_client import get_subscriptions_expiring_soon, update_subscription_expiration
from src.utils.logger import Logger

async def refresh_expiring_subscriptions():
    expiring = await get_subscriptions_expiring_soon(threshold_minutes=15)

    for sub in expiring:
        try:
            Logger.log_info(f"### MICROSOFT SUBSCRIPTION 🔄 Tentativo di rinnovo per subscription: {sub['subscription_id']} (email: {sub.get('email', 'unknown')})")
            
            renewed = await renew_subscription(sub["access_token"], sub["subscription_id"])
            new_expiration = renewed["expirationDateTime"]

            await update_subscription_expiration(sub["subscription_id"], new_expiration)
            Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ Subscription rinnovata con successo: {sub['subscription_id']}")

        except Exception as e:
            Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore nel rinnovo della subscription {sub['subscription_id']} (email: {sub.get('email', 'unknown')}): {str(e)}")
            # Log più dettagliato per capire il tipo di errore
            if "ValidationError" in str(e):
                Logger.log_error(f"### MICROSOFT SUBSCRIPTION 🔍 Errore di validazione webhook - Microsoft non riesce a validare l'endpoint")
            elif "400" in str(e):
                Logger.log_error(f"### MICROSOFT SUBSCRIPTION 🔍 Errore 400 - Bad Request dal Graph API")
            elif "401" in str(e):
                Logger.log_error(f"### MICROSOFT SUBSCRIPTION 🔍 Errore 401 - Token di accesso scaduto o non valido")