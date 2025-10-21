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
        print(f"🔍 Richiesta Gmail API - startHistoryId: {start_history_id}")
        
        # Prima verifica: ottieni l'historyId corrente della mailbox
        try:
            profile = service.users().getProfile(userId='me').execute()
            current_history_id = profile.get('historyId')
            print(f"📮 HistoryId corrente mailbox: {current_history_id}")
            print(f"📊 Differenza: {int(current_history_id) - int(start_history_id) if current_history_id and start_history_id else 'N/A'}")
        except Exception as e:
            print(f"⚠️ Errore ottenimento profile: {e}")
        
        # Proviamo con tutti i tipi di history per debugging
        response = service.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            # Temporaneamente rimuoviamo il filtro per vedere tutti gli eventi
            # historyTypes=['messageAdded']
        ).execute()

        print(f"📊 Risposta Gmail API: {len(response.get('history', []))} record di history")
        
        # Debug: mostra tutti gli eventi history per capire cosa succede
        for i, history_record in enumerate(response.get('history', []), 1):
            print(f"📝 History record #{i}:")
            if 'messages' in history_record:
                print(f"   📧 {len(history_record['messages'])} messaggi")
            if 'messagesAdded' in history_record:
                print(f"   ➕ {len(history_record['messagesAdded'])} messaggi aggiunti")
            if 'messagesDeleted' in history_record:
                print(f"   ➖ {len(history_record['messagesDeleted'])} messaggi eliminati")
            if 'labelsAdded' in history_record:
                print(f"   🏷️➕ {len(history_record['labelsAdded'])} labels aggiunte")
            if 'labelsRemoved' in history_record:
                print(f"   🏷️➖ {len(history_record['labelsRemoved'])} labels rimosse")

        # Processa i messaggi aggiunti
        for history_record in response.get('history', []):
            # Cerca in messagesAdded (più preciso) o fallback su messages
            added_messages = history_record.get('messagesAdded', [])
            if not added_messages:
                added_messages = history_record.get('messages', [])
                
            for msg_record in added_messages:
                msg_id = msg_record.get('message', {}).get('id') or msg_record.get('id')
                if msg_id:
                    try:
                        # Ottieni il messaggio completo con format=full per avere il body
                        msg_data = service.users().messages().get(
                            userId='me', 
                            id=msg_id,
                            format='full'
                        ).execute()
                        messages.append(msg_data)
                        print(f"✅ Recuperato messaggio ID: {msg_id}")
                    except Exception as e:
                        print(f"❌ Errore recupero messaggio {msg_id}: {e}")

        # Aggiorna SEMPRE l'historyId al valore corrente della risposta
        new_history_id = response.get('historyId')
        if new_history_id:
            result = update_history_id(email, new_history_id)
            if result is False:
                log_error(f"Errore nell'aggiornamento dello historyId per {email}")
            else:
                log_info(f"HistoryId aggiornato per {email} da {start_history_id} a {new_history_id}")
                
            # Se non abbiamo trovato messaggi ma l'historyId è cambiato molto,
            # potrebbe esserci una desincronizzazione
            if not messages and str(new_history_id) != str(start_history_id):
                try:
                    # Converti entrambi a stringa per il controllo isdigit()
                    new_id_str = str(new_history_id)
                    start_id_str = str(start_history_id)
                    
                    if new_id_str.isdigit() and start_id_str.isdigit():
                        id_diff = int(new_id_str) - int(start_id_str)
                        if id_diff > 100:  # Se la differenza è significativa
                            print(f"🔄 Possibile desincronizzazione rilevata (diff: {id_diff}). HistoryId sincronizzato automaticamente.")
                except Exception as e:
                    print(f"⚠️ Errore calcolo differenza historyId: {e}")
        else:
            print(f"⚠️ Nessun historyId nella risposta API")

    except Exception as e:
        print(f"❌ Errore fetch Gmail per {email}: {e}")
        import traceback
        traceback.print_exc()

    return messages