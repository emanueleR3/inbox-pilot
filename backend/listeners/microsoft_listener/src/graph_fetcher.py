import httpx
from src.db_client import get_user_credentials
from src.utils.logger import log_info, log_error

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

def parse_microsoft_message(graph_data: dict, user_email: str) -> dict:
    """
    Converte il messaggio di Microsoft Graph nel formato standard per RabbitMQ.
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
        
        # Se è HTML, potresti voler estrarre solo il testo (opzionale)
        if body_content.get("contentType") == "html":
            # Per ora mantieni l'HTML così com'è
            pass
        
        # Data di ricezione
        received_datetime = graph_data.get("receivedDateTime", "")
        
        return {
            "provider": "microsoft",
            "user_email": user_email,
            "from": from_address,
            "to": to_field,
            "subject": subject,
            "body_text": body_text,
            "date": received_datetime,
            "message_id": graph_data.get("id", ""),
            "thread_id": graph_data.get("conversationId", ""),
            "labels": [],  # Microsoft non usa labels come Gmail
            "timestamp": received_datetime
        }
    except Exception as e:
        log_error(f"Errore nel parsing del messaggio Microsoft: {str(e)}", e)
        return None

async def fetch_new_message(user_id: str, message_id: str):
    """
    Recupera la mail completa tramite Microsoft Graph e la converte nel formato standard.
    """
    try:
        log_info(f"📧 MICROSOFT - Recupero messaggio {message_id} per utente {user_id}")
        
        # Recupera access token dal DB per l'utente
        credentials = await get_user_credentials(user_id)
        access_token = credentials.get("access_token")
        user_email = credentials.get("email", user_id)

        url = f"{GRAPH_BASE_URL}/users/{user_id}/messages/{message_id}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
            resp.raise_for_status()
            graph_data = resp.json()
            
            log_info(f"✅ MICROSOFT - Messaggio recuperato da Graph API: {graph_data.get('subject', 'No subject')}")
            
            # Converte nel formato standard
            parsed_message = parse_microsoft_message(graph_data, user_email)
            
            if parsed_message:
                log_info(f"📨 MICROSOFT - Messaggio convertito per RabbitMQ da: {parsed_message.get('from')} oggetto: {parsed_message.get('subject')}")
                return parsed_message
            else:
                log_error("❌ MICROSOFT - Errore nella conversione del messaggio")
                return None
                
    except Exception as e:
        log_error(f"❌ MICROSOFT - Errore nel recupero messaggio {message_id}: {str(e)}", e)
        return None