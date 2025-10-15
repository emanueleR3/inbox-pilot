# refreshers/microsoft_subscription_refresher/src/db_client.py

from datetime import datetime, timedelta

# Simulazione DB
SUBSCRIPTIONS_DB = [
    {
        "subscription_id": "abc123",
        "user_id": "user_1",
        "access_token": "ACCESS_TOKEN_UTENTE",
        "expirationDateTime": "2025-10-09T15:00:00Z"
    },
    # ... altre subscription ... mockup
]

async def get_subscriptions_expiring_soon(threshold_hours=12):
    """
    Ritorna le subscription che scadranno entro X ore.
    """
    
    # TODO recupero dal DB reale

    soon = datetime.utcnow() + timedelta(hours=threshold_hours)
    expiring = [s for s in SUBSCRIPTIONS_DB if datetime.fromisoformat(s["expirationDateTime"].replace("Z", "")) <= soon]
    
    return expiring

async def update_subscription_expiration(subscription_id, new_expiration):
    """
    Aggiorna nel DB la nuova data di scadenza.
    """

    # TODO aggiornamento nel DB reale

    pass