import asyncio
import json
from src.gmail_fetcher import fetch_messages_for_user
from src.broker_client import RabbitMQPublisher 

publisher = RabbitMQPublisher()

async def process_pubsub_message(data: dict):
    """
    Funzione async che riceve notifiche Pub/Sub
    e fa fetch dei messaggi Gmail per l'utente
    """
    email = data.get("emailAddress")
    history_id = data.get("historyId")

    if not email or not history_id:
        print("❌ Messaggio Pub/Sub non valido:", data)
        return
    
    print(f"🔔 NOTIFICA RICEVUTA per {email} - historyId: {history_id}")
    
    # Usa l'historyId salvato nel DB se disponibile
    start_history_id = history_id  # Default: usa quello della notifica
    try:
        from src.db_client import get_user_credentials
        user_creds = get_user_credentials(email)
        saved_history_id = user_creds.get('history_id')
        
        if saved_history_id and str(saved_history_id) != str(history_id):
            start_history_id = saved_history_id
            
    except Exception as e:
        print(f"⚠️ Errore verifica historyId DB: {e}")
    
    # Connetti a RabbitMQ
    await publisher.connect()

    # Fetch async dei messaggi usando l'historyId corretto
    messages = await fetch_messages_for_user(email, start_history_id)

    # Se non ci sono messaggi, esci
    if not messages:
        print(f"📭 [{email}] Nessun messaggio nuovo da historyId {history_id}")
        return

    print(f"📧 [{email}] Trovati {len(messages)} nuovi messaggi!")

    # TODO
    # Salvare nel DB il messaggio ricevuto all'interno della tabella "threads"
    # Vedere tutta la logica per controllare se la mail sta rispondendo a un thread esistente
    # Vedere se sono presenti allegati e salvare il message id nel record del DB

    # TODO (per scalabilità)
    # prendere in considerazione di scaricare gli allegati e caricarli su uno storage esterno (es. S3, GCS)
    # aggiungre nel json del messaggio il link all'allegato "url_attachment": "https://..."

    # Modalità TEST: stampiamo i messaggi invece di inviarli a RabbitMQ
    for i, msg in enumerate(messages, 1):
        payload = _serialize_gmail_message(email, msg, history_id)
        await publisher.publish_message(payload)

    print(f"✅ [{email}] Processati {len(messages)} messaggi → inviati a RabbitMQ")

def _serialize_gmail_message(user_email: str, message: dict, history_id: str) -> dict:
    """
    Converte un messaggio Gmail API in un payload standard per il broker.
    """
    headers = {h["name"]: h["value"] for h in message.get("payload", {}).get("headers", [])}
    
    # Estrai il corpo del messaggio
    body_text = _extract_message_body(message.get("payload", {}))
    
    payload = {
        "provider": "gmail",
        "user_email": user_email,
        "history_id": history_id,
        "message_id": message.get("id"),
        "thread_id": message.get("threadId"),
        "subject": headers.get("Subject"),
        "from": headers.get("From"),
        "to": headers.get("To"),
        "cc": headers.get("Cc"),
        "bcc": headers.get("Bcc"),
        "date": headers.get("Date"),
        "snippet": message.get("snippet"),
        "body_text": body_text,
        "timestamp": message.get("internalDate"),
        "labels": message.get("labelIds", []),
        "attachments": [],
    }
    return payload

def _extract_message_body(payload: dict) -> str:
    """
    Estrae il corpo del messaggio dal payload Gmail.
    """
    import base64
    
    # Se il messaggio ha parts multiple (multipart)
    if "parts" in payload:
        for part in payload["parts"]:
            # Cerca la parte text/plain
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                try:
                    body_data = part["body"]["data"]
                    decoded = base64.urlsafe_b64decode(body_data + '==').decode('utf-8')
                    return decoded
                except Exception:
                    continue
            
            # Se non trova text/plain, prova text/html
            elif part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                try:
                    body_data = part["body"]["data"]
                    decoded = base64.urlsafe_b64decode(body_data + '==').decode('utf-8')
                    return decoded
                except Exception:
                    continue
    
    # Se il messaggio è semplice (non multipart)
    elif payload.get("body", {}).get("data"):
        try:
            body_data = payload["body"]["data"]
            decoded = base64.urlsafe_b64decode(body_data + '==').decode('utf-8')
            return decoded
        except Exception:
            pass
    
    return ""

# ESEMPIO DI COME SCARICARE GLI ALLEGATI E CARICARLI SU STORAGE ESTERNO
"""
import base64
import aiohttp
from googleapiclient.discovery import build

async def fetch_attachments(service, user_id, message):
    attachments_info = []

    for part in message["payload"].get("parts", []):
        if part.get("filename"):
            attach_id = part["body"].get("attachmentId")
            if not attach_id:
                continue
            attachment = (
                service.users()
                .messages()
                .attachments()
                .get(userId=user_id, messageId=message["id"], id=attach_id)
                .execute()
            )
            data = base64.urlsafe_b64decode(attachment["data"].encode("UTF-8"))

            # Upload to S3 / GCS / MinIO
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    "https://storage.myapp.com/upload",
                    data=data,
                    headers={"Content-Type": part["mimeType"]}
                ) as resp:
                    file_url = await resp.text()

            attachments_info.append({
                "filename": part["filename"],
                "mimeType": part["mimeType"],
                "url": file_url
            })

    return attachments_info
    """