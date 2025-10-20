import asyncio
from src.utils.gmail_api_client import get_service_for_user
from src.db_client import update_history_id
from src.utils.logger import log_error, log_info


async def fetch_messages_for_user(email: str, start_history_id: str):
    """
    Recupera messaggi Gmail da historyId in poi, async wrapper su fetch sync.
    """
    return await asyncio.to_thread(_fetch_messages_sync, email, start_history_id)

def _fetch_messages_sync(email: str, start_history_id: str):
    """
    Funzione sync che interagisce con Gmail API
    """
    service = get_service_for_user(email)
    
    messages = []
    try:
        response = service.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            historyTypes=['messageAdded']
        ).execute()

        for history_record in response.get('history', []):
            for msg in history_record.get('messages', []):
                msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
                messages.append(msg_data)

        # Aggiorna lo historyId nel database
        new_history_id = response.get('historyId')
        result = update_history_id(email, new_history_id)
        if result is False:
            log_error(f"Errore nell'aggiornamento dello historyId per {email}")
        else:
            log_info(f"HistoryId aggiornato per {email} a {new_history_id}")
        

    except Exception as e:
        print(f"Errore fetch Gmail per {email}: {e}")

    return messages