from src.db_client import get_tokens_expiring_soon, update_user_tokens
from src.utils.google_client import refresh_google_token

async def refresh_google_tokens():
    expiring_tokens = await get_tokens_expiring_soon(threshold_minutes=15)

    for token in expiring_tokens:
        try:
            refreshed = await refresh_google_token(token["refresh_token"])
            access_token = refreshed["access_token"]
            expires_in = refreshed.get("expires_in", 3600)

            await update_user_tokens(token["user_id"], access_token, expires_in)

            print(f"✅ Token rinnovato per utente {token['user_id']}")
        except Exception as e:
            print(f"❌ Errore nel rinnovo token per utente {token['user_id']}: {e}")