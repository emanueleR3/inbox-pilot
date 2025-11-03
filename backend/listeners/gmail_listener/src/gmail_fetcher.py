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
        # Recupera i messaggi dalla history Gmail
        response = service.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            historyTypes=['messageAdded']
        ).execute()

        # Processa i messaggi aggiunti
        for history_record in response.get('history', []):
            added_messages = history_record.get('messagesAdded', [])
                
            for msg_record in added_messages:
                msg_id = msg_record.get('message', {}).get('id')
                if msg_id:
                    try:
                        msg_data = service.users().messages().get(
                            userId='me', 
                            id=msg_id,
                            format='full'
                        ).execute()
                        messages.append(msg_data)
                    except Exception as e:
                        # Non loggiamo errori 404 come errori - sono normali
                        if "404" in str(e) or "not found" in str(e).lower():
                            log_info(f"Messaggio {msg_id} non più disponibile (404) - probabilmente già elaborato")
                        else:
                            log_error(f"Errore recupero messaggio {msg_id}: {e}")

        # Aggiorna l'historyId al valore corrente della risposta
        new_history_id = response.get('historyId')
        if new_history_id:
            result = update_history_id(email, new_history_id)
            if result is False:
                log_error(f"Errore nell'aggiornamento dello historyId per {email}")

    except Exception as e:
        log_error(f"Errore fetch Gmail per {email}: {e}")

    return messages