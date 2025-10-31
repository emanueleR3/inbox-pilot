import httpx
from src.db_client import get_user_credentials
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

def parse_microsoft_message(graph_data: dict, user_email: str) -> dict:
    """
    Converte il messaggio di Microsoft Graph nel formato standard per RabbitMQ.
    Usa gli header MIME standard come Gmail e IMAP.
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
        
        # Estrai il corpo del messaggio usando la nuova funzione
        body_content = graph_data.get("body", {})
        body_text = _extract_body_content(body_content)
        
        # Data di ricezione
        received_datetime = graph_data.get("receivedDateTime", "")
        
        # Estrai gli header MIME se disponibili
        internet_message_headers = graph_data.get("internetMessageHeaders", [])
        headers = {}
        if internet_message_headers:
            headers = {h.get("name", "").lower(): h.get("value", "") for h in internet_message_headers}
        
        # Usa internetMessageId come Message-ID standard (già presente nel payload principale)
        message_id = graph_data.get("internetMessageId", "")
        # Rimuovi < > se presenti (come fatto per Gmail)
        if message_id and message_id.startswith('<') and message_id.endswith('>'):
            message_id = message_id[1:-1]
        
        # Cerca In-Reply-To negli header MIME (case-insensitive)
        thread_id = headers.get("in-reply-to", "")
        # Rimuovi < > se presenti
        if thread_id and thread_id.startswith('<') and thread_id.endswith('>'):
            thread_id = thread_id[1:-1]
        # Se non c'è In-Reply-To, usa "no" come fatto per Gmail e IMAP
        if not thread_id:
            thread_id = "no"
        
        return {
            "provider": "microsoft",
            "user_email": user_email,
            "from": from_address,
            "to": to_field,
            "subject": subject,
            "body_text": body_text,
            "date": received_datetime,
            "message_id": message_id,  # Usa internetMessageId (header MIME standard)
            "thread_id": thread_id,   # Usa In-Reply-To header MIME o "no" se è None
            "labels": [],  # Microsoft non usa labels come Gmail
            "timestamp": received_datetime
        }
    except Exception as e:
        log_error(f"Errore nel parsing del messaggio Microsoft: {str(e)}", e)
        return None

async def fetch_new_message(subscription_id: str, message_id: str, actual_user_id: str):
    """
    Recupera la mail completa tramite Microsoft Graph e la converte nel formato standard.
    """
    try:
        log_info(f"📧 MICROSOFT - Recupero messaggio {message_id} per subscription {subscription_id}, user {actual_user_id}")
        
        # Recupera access token dal DB usando il subscription_id
        credentials = await get_user_credentials(subscription_id)
        access_token = credentials.get("access_token")
        user_email = credentials.get("email", actual_user_id)

        url = f"{GRAPH_BASE_URL}/users/{actual_user_id}/messages/{message_id}?$select=*,internetMessageHeaders"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
            resp.raise_for_status()
            graph_data = resp.json()
            
            # Converte nel formato standard
            parsed_message = parse_microsoft_message(graph_data, user_email)
            
            if parsed_message:
                return parsed_message
            else:
                log_error("❌ MICROSOFT - Errore nella conversione del messaggio")
                return None
                
    except Exception as e:
        log_error(f"❌ MICROSOFT - Errore nel recupero messaggio {message_id} per subscription {subscription_id}: {str(e)}", e)
        return None