import httpx
from src.db_client import get_user_credentials
from src.utils.logger import log_info, log_error

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

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
        
        # Estrai il corpo del messaggio
        body_content = graph_data.get("body", {})
        body_text = body_content.get("content", "")
        
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
            
            # DEBUG: Stampa il payload completo di Microsoft Graph per analisi
            import json
            log_info(f"🔍 DEBUG MICROSOFT GRAPH PAYLOAD per messaggio {message_id}:")
            log_info(json.dumps(graph_data, indent=2, ensure_ascii=False))
            
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