from datetime import datetime, timedelta

# Simulazione DB
TOKENS_DB = [
    {
        "user_id": "user_1",
        "provider": "google",
        "access_token": "OLD_ACCESS_TOKEN",
        "refresh_token": "REFRESH_TOKEN",
        "expires_at": "2025-10-09T14:00:00Z"
    },
    # altri utenti...
]

async def get_tokens_expiring_soon(threshold_minutes=15):
    """
    Ritorna i token che scadranno entro X minuti.
    """
    # TODO recupero dal DB reale

    soon = datetime.utcnow() + timedelta(minutes=threshold_minutes)
    expiring = [t for t in TOKENS_DB if datetime.fromisoformat(t["expires_at"].replace("Z", "")) <= soon]
    
    return expiring

async def update_user_tokens(user_id: str, access_token: str, expires_in: int):
    """
    Aggiorna i token dell'utente nel DB.
    """
    # TODO aggiornamento nel DB reale
    pass