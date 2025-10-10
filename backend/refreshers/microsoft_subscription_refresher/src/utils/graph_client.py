import httpx
from datetime import datetime, timedelta

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

    async with httpx.AsyncClient() as client:
        resp = await client.patch(f"{GRAPH_URL}/{subscription_id}", json=data, headers=headers)
        if resp.status_code not in [200, 202]:
            raise Exception(f"Errore nel rinnovo subscription {subscription_id}: {resp.status_code}, {resp.text}")
        return resp.json()