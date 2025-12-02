import asyncio
import json
import os
import re
import html
from src.gmail_fetcher import fetch_messages_for_user
from src.broker_client import RabbitMQPublisher 
from src.utils.logger import log_info 

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

    # Se non ci sono messaggi, stampa log consolidato e esci
    if not messages:
        log_info(f"📧 Notifica per [{email}] - 0 nuovi messaggi")
        return

    # Filtra i messaggi per escludere quelli inviati dalla stessa email
    filtered_messages = []
    draft_count = 0
    
    for msg in messages:
        payload = _serialize_gmail_message(email, msg, history_id)
        sender_email = _extract_email_from_header(payload.get('from', ''))
        labels = payload.get('labels', [])

        print(f"\n\n===========\nDEBUG:\nSender Payload: {payload}\n===========\n\n")

        # Salta i messaggi con label DRAFT (bozze)
        if 'DRAFT' in labels:
            draft_count += 1
            continue
            
        filtered_messages.append(payload)

    # Invia solo i messaggi filtrati a RabbitMQ
    for payload in filtered_messages:
        await publisher.publish_message(payload)

    # Log consolidato finale
    skipped_count = len(messages) - len(filtered_messages)
    if draft_count > 0:
        log_info(f"📧 Notifica per [{email}] - {len(messages)} nuovi messaggi; {skipped_count}/{len(messages)} scartati (motivo: draft)")
    else:
        log_info(f"📧 Notifica per [{email}] - {len(messages)} nuovi messaggi; {skipped_count}/{len(messages)} scartati")

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

    thread_id = message.get("threadId")
    if thread_id:
        # thread_id = _clean_message_id(thread_id) # Non serve pulire il threadId di solito, ma se vuoi mantenerlo:
        print(f"\n\n===========\nDEBUG:\nThread ID: {thread_id}\n===========\n\n")
    
    # Cerca in-reply-to in modo case-insensitive e rimuovi < >
    reply_to_id = headers_lower.get("in-reply-to")
    if reply_to_id:
        reply_to_id = _clean_message_id(reply_to_id)
    else:
        reply_to_id = "no"
    
    # Determina se è un'email no-reply
    is_no_reply = _is_no_reply_email(headers_lower.get("from", ""))
    
    # Determina se è un messaggio inviato dall'account stesso
    sender_email = _extract_email_from_header(headers_lower.get("from", ""))
    labels = message.get("labelIds", [])
    is_sent = (sender_email and sender_email.lower() == user_email.lower()) or 'SENT' in labels
    
    # Gestisci il campo 'to' con fallback più informativi
    to_field = headers_lower.get("to")
    if not to_field:
        # Se è BCC, potrebbe non esserci il campo To
        if headers_lower.get("bcc"):
            to_field = "BCC"
        # Se è una email inviata, usa il Delivered-To o X-Original-To
        elif is_sent:
            to_field = headers_lower.get("delivered-to") or headers_lower.get("x-original-to") or user_email
        # Se non è presente, usa l'account corrente come fallback
        else:
            to_field = user_email
    
    # Estrai metadata degli allegati (senza scaricarli)
    attachments_metadata = _extract_attachments_metadata(message.get("payload", {}))
    
    payload = {
        "provider": "gmail",
        "user_email": user_email,
        "history_id": history_id,
        "message_id": message_id,  # Usa header Message-Id IMAP standard (case-insensitive, senza < >)
        "reply_to_id": reply_to_id,   # Usa header In-Reply-To IMAP o "no" se è None (case-insensitive, senza < >)
        "subject": headers_lower.get("subject"),
        "from": headers_lower.get("from"),
        "to": to_field,
        "cc": headers_lower.get("cc"),
        "bcc": headers_lower.get("bcc"),
        "date": headers_lower.get("date"),
        "snippet": message.get("snippet"),
        "body_text": body_text,
        "timestamp": message.get("internalDate"),
        "labels": message.get("labelIds", []),
        "attachments": attachments_metadata,
        "no_reply": is_no_reply,
        "is_sent": is_sent,
        "original_thread_id": thread_id
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

def _is_no_reply_email(from_header: str) -> bool:
    """
    Determina se un'email proviene da un indirizzo no-reply.
    Esempi:
    - "no-reply@example.com" -> True
    - "noreply@example.com" -> True
    - "do-not-reply@example.com" -> True
    - "support@example.com" -> False
    """
    if not from_header:
        return False
    
    email = _extract_email_from_header(from_header)
    if not email:
        return False
    
    email_lower = email.lower()
    no_reply_patterns = [
        'no-reply', 'noreply', 'do-not-reply', 'donotreply',
        'no_reply', 'donot-reply', 'auto-reply', 'autoreply',
        'mailer-daemon', 'postmaster', 'bounce'
    ]
    
    return any(pattern in email_lower for pattern in no_reply_patterns)

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

def _extract_attachments_metadata(payload: dict) -> list:
    """
    Estrae i metadata degli allegati dal payload Gmail senza scaricarli.
    
    Args:
        payload: Payload del messaggio Gmail
        
    Returns:
        Lista di metadata degli allegati: [{"attachment_id": "...", "filename": "...", "mime_type": "...", "size": 123}]
    """
    attachments = []
    
    def _extract_from_parts(parts: list):
        """Estrae ricorsivamente allegati dalle parti del messaggio."""
        for part in parts:
            # Se questa parte ha sottoparti, esplora ricorsivamente
            if "parts" in part:
                _extract_from_parts(part["parts"])
            
            # Se ha un filename ed è un allegato
            filename = part.get("filename")
            if filename and part.get("body", {}).get("attachmentId"):
                attachment_id = part["body"]["attachmentId"]
                mime_type = part.get("mimeType", "application/octet-stream")
                size = part.get("body", {}).get("size", 0)
                
                attachments.append({
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "mime_type": mime_type,
                    "size": size
                })
    
    # Se il messaggio ha parti multiple (multipart)
    if "parts" in payload:
        _extract_from_parts(payload["parts"])
    
    return attachments
