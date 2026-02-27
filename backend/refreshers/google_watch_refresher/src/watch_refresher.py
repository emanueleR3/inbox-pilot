import asyncio
from datetime import datetime
from src.db_client import get_all_active_users, get_user_credentials
from src.utils.google_client import renew_gmail_watch
from src.utils.logger import Logger


async def refresh_gmail_watches():
    """
    Rinnova la watch Gmail (Pub/Sub push notification) per tutti gli utenti Google attivi.

    La Gmail watch API è idempotente: richiamare users().watch() su un utente
    che ha già una watch attiva la sostituisce con una nuova, estendendo
    l'expiration di ~7 giorni. Pertanto è sicuro chiamarla periodicamente
    senza bisogno di verificare lo stato corrente.

    Riferimento: https://developers.google.com/gmail/api/guides/push#renewing_mailbox_updates
    """
    emails = get_all_active_users()

    if not emails:
        Logger.log_info("### GOOGLE WATCH ⏰✅ Nessun utente attivo da rinnovare.")
        return

    Logger.log_info(f"### GOOGLE WATCH 🔄 Inizio rinnovo watch per {len(emails)} utenti...")

    success_count = 0
    error_count = 0

    for email in emails:
        try:
            creds = get_user_credentials(email)

            if not creds.get("access_token"):
                Logger.log_error(f"### GOOGLE WATCH ⚠️ Access token mancante per {email}, salto.")
                error_count += 1
                continue

            # Esegui la chiamata bloccante in un thread separato per non bloccare l'event loop
            response = await asyncio.to_thread(
                renew_gmail_watch,
                creds["access_token"],
                creds["refresh_token"],
            )

            expiration_ms = response.get("expiration")
            if expiration_ms:
                expiration_dt = datetime.utcfromtimestamp(int(expiration_ms) / 1000)
                Logger.log_info(
                    f"### GOOGLE WATCH ✅ Watch rinnovata per {email} — "
                    f"scadenza: {expiration_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                )
            else:
                Logger.log_info(f"### GOOGLE WATCH ✅ Watch rinnovata per {email}")

            success_count += 1

        except Exception as e:
            Logger.log_error(f"### GOOGLE WATCH ❌ Errore rinnovo watch per {email}: {str(e)}")
            error_count += 1

    Logger.log_info(
        f"### GOOGLE WATCH 📊 Rinnovo completato: {success_count} successi, {error_count} errori "
        f"su {len(emails)} utenti totali."
    )
