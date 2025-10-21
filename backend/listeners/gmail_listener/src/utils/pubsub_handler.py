import asyncio
import json
from src.gmail_fetcher import fetch_messages_for_user
# from src.broker_client import RabbitMQPublisher 

# publisher = RabbitMQPublisher()

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
    
    # Non connettiamo più a RabbitMQ in modalità test TODO
    # await publisher.connect()

    # Fetch async dei messaggi
    messages = await fetch_messages_for_user(email, history_id)

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
        
        print(f"\n📨 MESSAGGIO #{i} ricevuto:")
        print("=" * 80)
        print(f"📧 Da: {payload.get('from', 'N/A')}")
        print(f"📧 A: {payload.get('to', 'N/A')}")
        print(f"📧 Oggetto: {payload.get('subject', 'N/A')}")
        print(f"📧 Data: {payload.get('date', 'N/A')}")
        print(f"📧 Thread ID: {payload.get('thread_id', 'N/A')}")
        print(f"📧 Message ID: {payload.get('message_id', 'N/A')}")
        print(f"📧 Labels: {', '.join(payload.get('labels', []))}")
        print(f"📧 Snippet: {payload.get('snippet', 'N/A')}")
        print("\n� CORPO DEL MESSAGGIO:")
        print("-" * 40)
        body = payload.get('body_text', 'N/A')
        # Mostra massimo 1000 caratteri per non intasare i log
        if len(body) > 1000:
            print(f"{body[:1000]}...")
            print(f"[... troncato - lunghezza totale: {len(body)} caratteri]")
        else:
            print(body)
        print("-" * 40)
        
        print(f"📧 Timestamp: {payload.get('timestamp', 'N/A')}")
        print("=" * 80)
        
        # await publisher.publish_message(payload)  # Commentato per il test TODO

    print(f"✅ [{email}] Processati {len(messages)} messaggi (MODALITÀ TEST - non inviati a RabbitMQ)")

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
        # eventuali placeholder per allegati
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
                    # Decodifica da base64url
                    decoded = base64.urlsafe_b64decode(body_data + '==').decode('utf-8')
                    return decoded
                except Exception as e:
                    print(f"⚠️ Errore decodifica body text/plain: {e}")
            
            # Se non trova text/plain, prova text/html
            elif part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                try:
                    body_data = part["body"]["data"]
                    decoded = base64.urlsafe_b64decode(body_data + '==').decode('utf-8')
                    return f"[HTML] {decoded[:500]}..."  # Tronca l'HTML
                except Exception as e:
                    print(f"⚠️ Errore decodifica body text/html: {e}")
    
    # Se il messaggio è semplice (non multipart)
    elif payload.get("body", {}).get("data"):
        try:
            body_data = payload["body"]["data"]
            decoded = base64.urlsafe_b64decode(body_data + '==').decode('utf-8')
            return decoded
        except Exception as e:
            print(f"⚠️ Errore decodifica body semplice: {e}")
    
    # Fallback: usa solo lo snippet
    return "Corpo del messaggio non disponibile"

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