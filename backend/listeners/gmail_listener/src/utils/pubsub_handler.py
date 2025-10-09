import asyncio
from src.gmail_fetcher import fetch_messages_for_user
# from src.utils.broker_client import publish_messages  # pubblicazione su message broker

async def process_pubsub_message(data: dict):
    """
    Funzione async che riceve notifiche Pub/Sub
    e fa fetch dei messaggi Gmail per l’utente
    """
    email = data.get("emailAddress")
    history_id = data.get("historyId")

    if not email or not history_id:
        print("Messaggio Pub/Sub non valido:", data)
        return

    # Fetch async dei messaggi
    messages = await fetch_messages_for_user(email, history_id)

    # TODO
    # Salvare nel DB il messaggio ricevuto all'interno della tabella "threads"
    # Vedere tutta la logica per controllare se la mail sta rispondendo a un thread esistente
    # Vedere se sono presenti allegati e salvare il message id nel record del DB

    # TODO (per scalabilità)
    # prendere in considerazione di scaricare gli allegati e caricarli su uno storage esterno (es. S3, GCS)
    # aggiungre nel json del messaggio il link all'allegato "url_attachment": "https://..."

    # TODO
    # Qui invia messaggi al broker RabbitMQ

    print(f"[{email}] Fetched {len(messages)} messages from historyId {history_id}")



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