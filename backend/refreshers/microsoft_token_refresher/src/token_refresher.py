from src.db_client import get_tokens_expiring_soon, update_user_tokens
from src.utils.microsoft_client import refresh_microsoft_token

async def refresh_microsoft_tokens():
    expiring_tokens = await get_tokens_expiring_soon(threshold_minutes=15)

    for token in expiring_tokens:
        try:
            refreshed = await refresh_microsoft_token(token["refresh_token"])
            access_token = refreshed["access_token"]
            expires_in = refreshed.get("expires_in", 3600)
            new_refresh_token = refreshed.get("refresh_token")  # Microsoft può ruotarlo

            await update_user_tokens(
                token["email"],
                access_token,
                expires_in,
                new_refresh_token
            )

            print(f"✅ Token Microsoft rinnovato per utente {token['user_id']}")

        except Exception as e:
            print(f"❌ Errore nel rinnovo token Microsoft per utente {token['user_id']}: {e}")