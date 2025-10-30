from src.db_client import get_tokens_expiring_soon, update_user_tokens
from src.utils.microsoft_client import refresh_microsoft_token
from src.utils.logger import Logger

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

            Logger.log_info(f"### MICROSOFT ✅ Token rinnovato con successo per utente {token['email']}")

        except Exception as e:
            Logger.log_error(f"### MICROSOFT ❌ Errore nel rinnovo del token per utente {token['email']}: {str(e)}")