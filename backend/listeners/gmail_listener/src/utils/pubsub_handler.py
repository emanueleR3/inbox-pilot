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

    # Filtra i messaggi per escludere quelli inviati dalla stessa email
    filtered_messages = []
    for msg in messages:
        payload = _serialize_gmail_message(email, msg, history_id)
        sender_email = _extract_email_from_header(payload.get('from', ''))
        labels = payload.get('labels', [])
        
        # Se il mittente è la stessa email dell'account, salta questo messaggio
        if sender_email and sender_email.lower() == email.lower():
            print(f"🚫 Messaggio saltato - inviato dalla stessa email ({sender_email}): {payload.get('subject', 'N/A')}")
            continue
        
        # Salta anche i messaggi con label SENT (email inviate)
        if 'SENT' in labels:
            print(f"🚫 Messaggio saltato - ha label SENT: {payload.get('subject', 'N/A')}")
            continue
            
        # Salta i messaggi con label DRAFT (bozze)
        if 'DRAFT' in labels:
            print(f"🚫 Messaggio saltato - ha label DRAFT: {payload.get('subject', 'N/A')}")
            continue
            
        filtered_messages.append(payload)

    # Se non ci sono messaggi da processare dopo il filtro
    if not filtered_messages:
        print(f"📭 [{email}] Nessun messaggio da processare dopo il filtro (tutti erano dalla stessa email)")
        return

    # Invia solo i messaggi filtrati a RabbitMQ
    for payload in filtered_messages:
        await publisher.publish_message(payload)

    print(f"✅ [{email}] Processati {len(filtered_messages)}/{len(messages)} messaggi → inviati a RabbitMQ (saltati {len(messages) - len(filtered_messages)} messaggi dalla stessa email)")

def _serialize_gmail_message(user_email: str, message: dict, history_id: str) -> dict:
    """
    Converte un messaggio Gmail API in un payload standard per il broker.
    """
    headers = {h["name"]: h["value"] for h in message.get("payload", {}).get("headers", [])}
    
    # Crea un dizionario case-insensitive per gli header
    headers_lower = {k.lower(): v for k, v in headers.items()}
    
    # Estrai il corpo del messaggio
    body_text = _extract_message_body(message.get("payload", {}))
    
    # Pulisce il corpo del messaggio
    if body_text:
        body_text = _clean_gmail_body(body_text)
    
    # Cerca message-id in modo case-insensitive e rimuovi < >
    message_id = headers_lower.get("message-id")
    if message_id:
        message_id = _clean_message_id(message_id)
    
    # Cerca in-reply-to in modo case-insensitive e rimuovi < >
    thread_id = headers_lower.get("in-reply-to")
    if thread_id:
        thread_id = _clean_message_id(thread_id)
    else:
        thread_id = "no"
    
    payload = {
        "provider": "gmail",
        "user_email": user_email,
        "history_id": history_id,
        "message_id": message_id,  # Usa header Message-Id IMAP standard (case-insensitive, senza < >)
        "thread_id": thread_id,   # Usa header In-Reply-To IMAP o "no" se è None (case-insensitive, senza < >)
        "subject": headers_lower.get("subject"),
        "from": headers_lower.get("from"),
        "to": headers_lower.get("to"),
        "cc": headers_lower.get("cc"),
        "bcc": headers_lower.get("bcc"),
        "date": headers_lower.get("date"),
        "snippet": message.get("snippet"),
        "body_text": body_text,
        "timestamp": message.get("internalDate"),
        "labels": message.get("labelIds", []),
        "attachments": [],
    }
    return payload

def _clean_message_id(message_id: str) -> str:
    """
    Rimuove i caratteri < > dai Message-ID se presenti.
    Esempi:
    - "<123456@gmail.com>" -> "123456@gmail.com"
    - "123456@gmail.com" -> "123456@gmail.com"
    """
    if not message_id:
        return message_id
    
    # Rimuovi < > se presenti all'inizio e alla fine
    if message_id.startswith('<') and message_id.endswith('>'):
        return message_id[1:-1]
    
    return message_id

def _extract_email_from_header(from_header: str) -> str:
    """
    Estrae l'indirizzo email dall'header 'From'.
    Esempi:
    - "Emanuele Romano <dev1@example.com>" -> "dev1@example.com"
    - "dev1@example.com" -> "dev1@example.com"
    """
    if not from_header:
        return ""
    
    import re
    # Regex per estrarre l'email tra < > o l'email diretta
    email_match = re.search(r'<([^>]+)>|([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', from_header)
    if email_match:
        return email_match.group(1) or email_match.group(2)
    
    return ""

def _clean_gmail_body(body_text: str) -> str:
    """
    Pulisce il corpo del messaggio Gmail rimuovendo caratteri indesiderati.
    """
    import re
    import html
    
    if not body_text:
        return ""
    
    # Decodifica entità HTML se presenti
    cleaned = html.unescape(body_text)
    
    # Rimuove quoted-printable artifacts
    cleaned = re.sub(r'=\d{2}', '', cleaned)  # Rimuove =20, =3D, etc.
    cleaned = re.sub(r'=\n', '', cleaned)     # Rimuove soft line breaks
    
    # Se sembra essere HTML, estrae il testo
    if '<' in cleaned and '>' in cleaned:
        # Rimuove script e style
        cleaned = re.sub(r'<script[^>]*>.*?</script>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        
        # Sostituisce i br con newline
        cleaned = re.sub(r'<br[^>]*>', '\n', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'</p>', '\n\n', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'</div>', '\n', cleaned, flags=re.IGNORECASE)
        
        # Rimuove tutti i tag HTML
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
    
    # Rimuove caratteri di controllo e normalizza gli spazi
    cleaned = re.sub(r'[\r\n\t]+', '\n', cleaned)
    cleaned = re.sub(r' +', ' ', cleaned)
    
    # Rimuove righe vuote multiple consecutive
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    
    # Rimuove spazi all'inizio e fine delle righe
    lines = [line.strip() for line in cleaned.split('\n')]
    cleaned = '\n'.join(lines)
    
    return cleaned.strip()

def _extract_message_body(payload: dict) -> str:
    """
    Estrae il corpo del messaggio dal payload Gmail con supporto per strutture annidate.
    """
    import base64
    
    def _decode_body_data(body_data: str) -> str:
        """Helper per decodificare i dati base64 del corpo del messaggio."""
        try:
            # Aggiungi padding se necessario e decodifica
            decoded = base64.urlsafe_b64decode(body_data + '==').decode('utf-8')
            return decoded
        except Exception:
            return ""
    
    def _extract_from_parts(parts: list, prefer_plain=True) -> str:
        """
        Estrae ricorsivamente il contenuto dalle parti del messaggio.
        Args:
            parts: Lista delle parti del messaggio
            prefer_plain: Se True, preferisce text/plain a text/html
        """
        plain_text = ""
        html_text = ""
        
        for part in parts:
            mime_type = part.get("mimeType", "")
            
            # Se questa parte ha sottoparti, esplora ricorsivamente
            if "parts" in part:
                nested_result = _extract_from_parts(part["parts"], prefer_plain)
                if nested_result:
                    return nested_result
            
            # Se è text/plain e ha dati
            elif mime_type == "text/plain" and part.get("body", {}).get("data"):
                body_data = part["body"]["data"]
                plain_text = _decode_body_data(body_data)
                if plain_text and prefer_plain:
                    return plain_text
            
            # Se è text/html e ha dati
            elif mime_type == "text/html" and part.get("body", {}).get("data"):
                body_data = part["body"]["data"]
                html_text = _decode_body_data(body_data)
                if html_text and not prefer_plain:
                    return html_text
        
        # Ritorna il migliore contenuto trovato
        return plain_text or html_text
    
    # Se il messaggio ha parti multiple (multipart)
    if "parts" in payload:
        result = _extract_from_parts(payload["parts"])
        if result:
            return result
    
    # Se il messaggio è semplice (non multipart)
    elif payload.get("body", {}).get("data"):
        body_data = payload["body"]["data"]
        return _decode_body_data(body_data)
    
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