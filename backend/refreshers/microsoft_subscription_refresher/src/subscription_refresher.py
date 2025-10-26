# refreshers/microsoft_subscription_refresher/src/subscription_refresher.py
from src.utils.graph_client import renew_subscription
from src.db_client import get_subscriptions_expiring_soon, update_subscription_expiration
from src.utils.logger import Logger

async def refresh_expiring_subscriptions():
    expiring = await get_subscriptions_expiring_soon(threshold_hours=12)

    for sub in expiring:
        try:
            renewed = await renew_subscription(sub["access_token"], sub["subscription_id"])
            new_expiration = renewed["expirationDateTime"]

            await update_subscription_expiration(sub["subscription_id"], new_expiration)
            Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ Subscription rinnovata con successo: {sub['subscription_id']}")

        except Exception as e:
            Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore nel rinnovo della subscription {sub['subscription_id']}: {str(e)}")