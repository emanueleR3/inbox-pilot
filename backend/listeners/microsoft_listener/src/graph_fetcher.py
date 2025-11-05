import httpx
from src.db_client import get_user_credentials_inbound, get_user_credentials_outbound
from src.utils.logger import log_info, log_error

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

def _extract_body_content(body_content: dict) -> str:
    """
    Estrae il contenuto del corpo del messaggio da Microsoft Graph.
    Gestisce sia text/plain che text/html, preferendo text/plain.
    """
    import re
    import html
    
    def _clean_text(text: str) -> str:
        """Pulisce il testo rimuovendo caratteri indesiderati."""
        if not text:
            return ""
        
        # Rimuove caratteri di controllo e normalizza gli spazi
        cleaned = re.sub(r'[\r\n\t]+', '\n', text)
        cleaned = re.sub(r' +', ' ', cleaned)
        
        # Rimuove righe vuote multiple consecutive
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
        
        # Rimuove spazi all'inizio e fine delle righe
        lines = [line.strip() for line in cleaned.split('\n')]
        cleaned = '\n'.join(lines)
        
        return cleaned.strip()
    
    def _html_to_text(html_content: str) -> str:
        """Converte HTML in testo semplice."""
        if not html_content:
            return ""
        
        # Rimuove script e style
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Sostituisce i br con newline
        text = re.sub(r'<br[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
        
        # Rimuove tutti i tag HTML
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decodifica entità HTML
        text = html.unescape(text)
        
        return _clean_text(text)
    
    if not body_content:
        return ""
    
    content = body_content.get("content", "")
    content_type = body_content.get("contentType", "").lower()
    
    if not content:
        return ""
    
    # Se è HTML, converte in testo
    if content_type == "html":
        return _html_to_text(content)
    
    # Se è testo, pulisce e ritorna
    return _clean_text(content)

def _extract_email_from_address(email_address: str) -> str:
    """
    Estrae l'indirizzo email dal campo Microsoft Graph.
    Esempi:
    - "Emanuele Romano <emanuele.romano@example.com>" -> "emanuele.romano@example.com"
    - "emanuele.romano@example.com" -> "emanuele.romano@example.com"
    """
    if not email_address:
        return ""
    
    import re
    # Regex per estrarre l'email tra < > o l'email diretta
    email_match = re.search(r'<([^>]+)>|([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', email_address)
    if email_match:
        return email_match.group(1) or email_match.group(2)
    
    return ""

def _is_no_reply_email(from_address: str) -> bool:
    """
    Determina se un'email proviene da un indirizzo no-reply.
    Esempi:
    - "no-reply@example.com" -> True
    - "noreply@example.com" -> True
    - "do-not-reply@example.com" -> True
    - "support@example.com" -> False
    """
    if not from_address:
        return False
    
    email = _extract_email_from_address(from_address)
    if not email:
        return False
    
    email_lower = email.lower()
    no_reply_patterns = [
        'no-reply', 'noreply', 'do-not-reply', 'donotreply',
        'no_reply', 'donot-reply', 'auto-reply', 'autoreply',
        'mailer-daemon', 'postmaster', 'bounce'
    ]
    
    return any(pattern in email_lower for pattern in no_reply_patterns)

def _extract_microsoft_attachments_metadata(graph_data: dict) -> list:
    """
    Estrae i metadata degli allegati da Microsoft Graph senza scaricarli.
    
    Args:
        graph_data: Dati del messaggio da Microsoft Graph
        
    Returns:
        Lista di metadata degli allegati
    """
    attachments = []
    
    # Microsoft Graph fornisce attachments come array separato
    graph_attachments = graph_data.get("attachments", [])
    
    log_info(f"📎 [MICROSOFT] Found {len(graph_attachments)} attachments in Graph data")
    
    for attachment in graph_attachments:
        attachment_type = attachment.get("@odata.type", "")
        log_info(f"📎 [MICROSOFT] Processing attachment type: {attachment_type}")
        
        # Controlla se è un file attachment (non inline)
        if attachment_type == "#microsoft.graph.fileAttachment":
            attachment_id = attachment.get("id", "")
            filename = attachment.get("name", "")
            mime_type = attachment.get("contentType", "application/octet-stream")
            size = attachment.get("size", 0)
            
            log_info(f"📎 [MICROSOFT] File attachment: {filename} ({size} bytes, {mime_type})")
            log_info(f"📎 [MICROSOFT] Attachment ID: '{attachment_id}'")
            
            if filename:  # Solo se ha un nome file valido
                attachments.append({
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "mime_type": mime_type,
                    "size": size
                })
        else:
            log_info(f"📎 [MICROSOFT] Skipping attachment type: {attachment_type}")
    
    log_info(f"📎 [MICROSOFT] Returning {len(attachments)} valid attachments")
    return attachments

def parse_microsoft_message(graph_data: dict, user_email: str, is_sent_message: bool = False) -> dict:
    """
    Converte il messaggio di Microsoft Graph nel formato standard per RabbitMQ.
    Ora include un flag per indicare se è un messaggio inviato.
    """
    try:
        # Estrai i campi principali
        subject = graph_data.get("subject", "")
        sender = graph_data.get("sender", {}).get("emailAddress", {})
        from_address = f"{sender.get('name', '')} <{sender.get('address', '')}>"
        
        # Gestisci i destinatari
        to_recipients = graph_data.get("toRecipients", [])
        to_addresses = []
        for recipient in to_recipients:
            email_addr = recipient.get("emailAddress", {})
            to_addresses.append(f"{email_addr.get('name', '')} <{email_addr.get('address', '')}>")
        to_field = ", ".join(to_addresses)
        
        # Gestisci i destinatari in CC
        cc_recipients = graph_data.get("ccRecipients", [])
        cc_addresses = []
        for recipient in cc_recipients:
            email_addr = recipient.get("emailAddress", {})
            cc_addresses.append(f"{email_addr.get('name', '')} <{email_addr.get('address', '')}>")
        cc_field = ", ".join(cc_addresses) if cc_addresses else None
        
        # Gestisci i destinatari in BCC (se disponibili)
        bcc_recipients = graph_data.get("bccRecipients", [])
        bcc_addresses = []
        for recipient in bcc_recipients:
            email_addr = recipient.get("emailAddress", {})
            bcc_addresses.append(f"{email_addr.get('name', '')} <{email_addr.get('address', '')}>")
        bcc_field = ", ".join(bcc_addresses) if bcc_addresses else None
        
        # Estrai il corpo del messaggio usando la nuova funzione
        body_content = graph_data.get("body", {})
        body_text = _extract_body_content(body_content)
        
        # Data di ricezione o invio
        received_datetime = graph_data.get("receivedDateTime", "")
        sent_datetime = graph_data.get("sentDateTime", "")
        # Usa sentDateTime per messaggi inviati, receivedDateTime per quelli ricevuti
        message_datetime = sent_datetime if is_sent_message else received_datetime
        
        # Estrai gli header MIME se disponibili
        internet_message_headers = graph_data.get("internetMessageHeaders", [])
        headers = {}
        if internet_message_headers:
            headers = {h.get("name", "").lower(): h.get("value", "") for h in internet_message_headers}
        
        # Usa internetMessageId come Message-ID standard
        message_id = graph_data.get("internetMessageId", "")
        if message_id and message_id.startswith('<') and message_id.endswith('>'):
            message_id = message_id[1:-1]
        
        # Salva anche l'ID interno di Microsoft Graph per downloads degli allegati
        microsoft_message_id = graph_data.get("id", "")
        
        # Cerca In-Reply-To negli header MIME
        reply_to_id = headers.get("in-reply-to", "")
        if reply_to_id and reply_to_id.startswith('<') and reply_to_id.endswith('>'):
            reply_to_id = reply_to_id[1:-1]
        if not reply_to_id:
            reply_to_id = "no"
        
        # Simula le labels per essere consistente con Gmail
        labels = []
        if is_sent_message:
            labels.append("SENT")
        else:
            labels.append("INBOX")
        
        # Determina se è un'email no-reply
        is_no_reply = _is_no_reply_email(from_address)
        
        # Estrai metadata degli allegati senza scaricarli
        attachments_metadata = _extract_microsoft_attachments_metadata(graph_data)
        
        return {
            "provider": "microsoft",
            "user_email": user_email,
            "from": from_address,
            "to": to_field,
            "cc": cc_field,
            "bcc": bcc_field,
            "subject": subject,
            "body_text": body_text,
            "date": message_datetime,
            "message_id": message_id,
            "microsoft_message_id": microsoft_message_id,  # ID interno per Microsoft Graph API
            "reply_to_id": reply_to_id,
            "labels": labels,  # Aggiungi SENT per messaggi inviati
            "timestamp": message_datetime,
            "is_sent": is_sent_message,  # Flag aggiuntivo per identificare messaggi inviati
            "no_reply": is_no_reply,
            "attachments": attachments_metadata,
        }
    except Exception as e:
        log_error(f"Errore nel parsing del messaggio Microsoft: {str(e)}", e)
        return None

async def fetch_new_message(subscription_id: str, message_id: str, actual_user_id: str, is_outbound: bool = False):
    """
    Recupera la mail completa tramite Microsoft Graph e la converte nel formato standard.
    Ora gestisce sia messaggi ricevuti che inviati.
    
    Args:
        subscription_id: ID della subscription Microsoft (encrypted)
        message_id: ID del messaggio
        actual_user_id: ID dell'utente Microsoft
        is_outbound: True se è una subscription outbound (SentItems), False se inbound (Inbox)
    """
    try:
        log_info(f"📧 MICROSOFT - Recupero messaggio {message_id} per subscription {subscription_id}, user {actual_user_id}, outbound={is_outbound}")
        
        # Recupera access token dal DB usando il subscription_id appropriato
        if is_outbound:
            credentials = await get_user_credentials_outbound(subscription_id)
        else:
            credentials = await get_user_credentials_inbound(subscription_id)
            
        access_token = credentials.get("access_token")
        user_email = credentials.get("email", actual_user_id)

        # Aggiungi parentFolderId per capire se è un messaggio inviato o ricevuto
        # Includi anche attachments per ottenere i metadata degli allegati
        url = f"{GRAPH_BASE_URL}/users/{actual_user_id}/messages/{message_id}?$select=*,internetMessageHeaders,parentFolderId&$expand=attachments"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
            resp.raise_for_status()
            graph_data = resp.json()
            
            # Per outbound subscriptions, sappiamo già che è un messaggio inviato
            # Per inbound, controlliamo la cartella parent
            if is_outbound:
                is_sent_message = True
            else:
                is_sent_message = await _is_sent_message(graph_data, access_token, actual_user_id)
            
            # Converte nel formato standard
            parsed_message = parse_microsoft_message(graph_data, user_email, is_sent_message)
            
            if parsed_message:
                log_info(f"✅ MICROSOFT - Messaggio {'inviato' if is_sent_message else 'ricevuto'} processato: {parsed_message.get('subject', 'N/A')}")
                return parsed_message
            else:
                log_error("❌ MICROSOFT - Errore nella conversione del messaggio")
                return None
                
    except Exception as e:
        log_error(f"❌ MICROSOFT - Errore nel recupero messaggio {message_id} per subscription {subscription_id}: {str(e)}", e)
        return None

async def _is_sent_message(graph_data: dict, access_token: str, user_id: str) -> bool:
    """
    Determina se il messaggio è stato inviato dall'utente controllando la cartella parent.
    """
    try:
        parent_folder_id = graph_data.get("parentFolderId")
        if not parent_folder_id:
            return False
        
        # Ottieni info sulla cartella parent
        url = f"{GRAPH_BASE_URL}/users/{user_id}/mailFolders/{parent_folder_id}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
            if resp.status_code == 200:
                folder_data = resp.json()
                folder_name = folder_data.get("displayName", "").lower()
                well_known_name = folder_data.get("wellKnownName", "").lower()
                
                # Controlla se è la cartella "Sent Items" o "Outbox"
                return (well_known_name in ["sentitems", "outbox"] or 
                       "sent" in folder_name or 
                       "inviati" in folder_name or
                       "outbox" in folder_name)
    except Exception as e:
        log_error(f"Errore nel determinare se il messaggio è inviato: {e}")
    
    return False