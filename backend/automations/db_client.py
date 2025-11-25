"""
Database client for automations module.
Handles connections to Supabase and retrieves user configurations.
"""

import os
from supabase import create_client, Client
from threading import Lock
from typing import Dict, Optional
from dotenv import load_dotenv

# Carica le variabili d'ambiente
load_dotenv()

# Client Supabase singleton
_supabase_client: Client | None = None
_client_lock = Lock()


def get_supabase_client() -> Client:
    """
    Ottiene il client Supabase utilizzando il pattern singleton con thread safety.
    """
    global _supabase_client
    if _supabase_client is None:
        with _client_lock:
            if _supabase_client is None:  # double-checked locking
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_KEY")
                
                if not supabase_url or not supabase_key:
                    raise ValueError("SUPABASE_URL e SUPABASE_KEY devono essere configurati nelle variabili d'ambiente")
                
                _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client


class UserConfiguration:
    """Model for user configuration thresholds from subscription_services table."""
    
    def __init__(self, data: Dict):
        self.email = data.get("email")
        self.service_id = data.get("service_id")
        self.confidence_response_threshold = data.get("confidence_response_threshold", 0.7)
        self.confidence_review_mail = data.get("confidence_review_mail", 0.8)
        self.priority_threshold = data.get("priority_threshold", 0.6)
        self.confidence_classification_threshold = data.get("confidence_classification_threshold", 0.75)
        self.urgent_meeting_threshold = data.get("urgent_meeting_threshold", 0.85)
        self.activated = data.get("activated", False)
        self.config_completed = data.get("config_completed", False)
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary for workflow state."""
        return {
            "email": self.email,
            "service_id": self.service_id,
            "confidence_response_threshold": self.confidence_response_threshold,
            "confidence_review_mail": self.confidence_review_mail,
            "priority_threshold": self.priority_threshold,
            "confidence_classification_threshold": self.confidence_classification_threshold,
            "urgent_meeting_threshold": self.urgent_meeting_threshold,
            "activated": self.activated,
            "config_completed": self.config_completed
        }
    
    def __repr__(self) -> str:
        return f"UserConfiguration(email={self.email}, activated={self.activated})"


async def get_user_configuration(box_email: str) -> Optional[UserConfiguration]:
    """
    Recupera la configurazione utente dalla tabella subscription_services.
    
    Args:
        box_email (str): Email della casella di posta (box_email del workflow)
        
    Returns:
        UserConfiguration: Configurazione utente con le threshold necessarie
        None: Se l'utente non è trovato o non è attivato
    """
    try:
        supabase = get_supabase_client()
        
        print(f"🔍 [DB_CLIENT] Retrieving configuration for email: {box_email}")
        
        # Query per ottenere la configurazione dell'utente
        response = supabase.table("subscription_services").select(
            "service_id, "
            "email, "
            "confidence_response_threshold, "
            "confidence_review_mail, "
            "priority_threshold, "
            "confidence_classification_threshold, "
            "urgent_meeting_threshold, "
            "activated, "
            "config_completed"
        ).eq("email", box_email).execute()
        
        if not response.data:
            print(f"⚠️ [DB_CLIENT] No configuration found for email: {box_email}")
            return None
        
        if len(response.data) > 1:
            print(f"⚠️ [DB_CLIENT] Multiple configurations found for email: {box_email}, using first one")
        
        user_data = response.data[0]
        user_config = UserConfiguration(user_data)
        
        # Verifica che l'utente sia attivato
        if not user_config.activated:
            print(f"❌ [DB_CLIENT] User {box_email} is not activated")
            return None
        
        # Verifica che la configurazione sia completata
        if not user_config.config_completed:
            print(f"⚠️ [DB_CLIENT] User {box_email} configuration is not completed")
        
        print(f"✅ [DB_CLIENT] Configuration retrieved for {box_email}")
        print(f"   📊 Response threshold: {user_config.confidence_response_threshold}")
        print(f"   📧 Review mail threshold: {user_config.confidence_review_mail}")
        print(f"   🔥 Priority threshold: {user_config.priority_threshold}")
        print(f"   🏷️ Classification threshold: {user_config.confidence_classification_threshold}")
        print(f"   ⚡ Urgent meeting threshold: {user_config.urgent_meeting_threshold}")
        
        return user_config
        
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error retrieving user configuration for {box_email}: {str(e)}")
        return None


def get_user_configuration_sync(box_email: str) -> Optional[UserConfiguration]:
    """
    Versione sincrona per recuperare la configurazione utente.
    Utilizzata dai nodi del workflow che non supportano async.
    
    Args:
        box_email (str): Email della casella di posta
        
    Returns:
        UserConfiguration: Configurazione utente con le threshold necessarie
        None: Se l'utente non è trovato o non è attivato
    """
    try:
        supabase = get_supabase_client()
        
        print(f"🔍 [DB_CLIENT] Retrieving configuration (sync) for email: {box_email}")
        
        # Query sincrona per ottenere la configurazione dell'utente
        response = supabase.table("subscription_services").select(
            "service_id, "
            "email, "
            "confidence_response_threshold, "
            "confidence_review_mail, "
            "priority_threshold, "
            "confidence_classification_threshold, "
            "urgent_meeting_threshold, "
            "activated, "
            "config_completed"
        ).eq("email", box_email).execute()
        
        if not response.data:
            print(f"⚠️ [DB_CLIENT] No configuration found for email: {box_email}")
            return None
        
        if len(response.data) > 1:
            print(f"⚠️ [DB_CLIENT] Multiple configurations found for email: {box_email}, using first one")
        
        user_data = response.data[0]
        user_config = UserConfiguration(user_data)
        
        # Verifica che l'utente sia attivato
        if not user_config.activated:
            print(f"❌ [DB_CLIENT] User {box_email} is not activated")
            return None
        
        # Verifica che la configurazione sia completata
        if not user_config.config_completed:
            print(f"⚠️ [DB_CLIENT] User {box_email} configuration is not completed, using defaults")
        
        print(f"✅ [DB_CLIENT] Configuration retrieved (sync) for {box_email}")
        print(f"   📊 Response threshold: {user_config.confidence_response_threshold}")
        print(f"   📧 Review mail threshold: {user_config.confidence_review_mail}")
        print(f"   🔥 Priority threshold: {user_config.priority_threshold}")
        print(f"   🏷️ Classification threshold: {user_config.confidence_classification_threshold}")
        print(f"   ⚡ Urgent meeting threshold: {user_config.urgent_meeting_threshold}")
        
        return user_config
        
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error retrieving user configuration (sync) for {box_email}: {str(e)}")
        return None


def get_default_configuration() -> UserConfiguration:
    """
    Ritorna una configurazione di default quando non è possibile recuperare quella dell'utente.
    
    Returns:
        UserConfiguration: Configurazione con valori di default
    """
    default_data = {
        "email": "unknown",
        "service_id": None,
        "confidence_response_threshold": 0.7,
        "confidence_review_mail": 0.8,
        "priority_threshold": 0.6,
        "confidence_classification_threshold": 0.75,
        "urgent_meeting_threshold": 0.85,
        "activated": True,
        "config_completed": False
    }
    
    print(f"⚙️ [DB_CLIENT] Using default configuration")
    return UserConfiguration(default_data)


async def test_database_connection() -> bool:
    """
    Testa la connessione al database Supabase.
    
    Returns:
        bool: True se la connessione è riuscita, False altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        # Test query semplice
        response = supabase.table("subscription_services").select("service_id").limit(1).execute()
        
        print(f"✅ [DB_CLIENT] Database connection test successful")
        return True
        
    except Exception as e:
        print(f"❌ [DB_CLIENT] Database connection test failed: {str(e)}")
        return False


async def insert_notification(email: str, notification_type: str, message_id: str, text: str = None) -> bool:
    """
    Inserisce una nuova notifica nella tabella notifications.
    
    Args:
        email (str): Email dell'utente (box_email)
        notification_type (str): Tipo di notifica (es. MAIL_NOT_PERMITTED)
        message_id (str): ID del messaggio email
        text (str, optional): Testo aggiuntivo della notifica
        
    Returns:
        bool: True se l'inserimento è avvenuto con successo, False altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        # Prepara i dati da inserire
        notification_data = {
            "email": email,
            "type": notification_type,
            "message_id": message_id
        }
        
        # Aggiungi il testo se fornito
        if text:
            notification_data["text"] = text
        
        # Inserisci la notifica nel database
        response = supabase.table("notifications").insert(notification_data).execute()
        
        if not response.data:
            print(f"❌ [DB_CLIENT] Failed to insert notification for {email}")
            return False
        
        inserted_notification = response.data[0]
        notification_id = inserted_notification.get("notification_id")

        return True
        
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error inserting notification for {email}: {str(e)}")
        return False


def insert_notification_sync(email: str, notification_type: str, message_id: str, text: str = None) -> bool:
    """
    Versione sincrona per inserire una notifica.
    Utilizzata dai nodi del workflow che non supportano async.
    
    Args:
        email (str): Email dell'utente (box_email)
        notification_type (str): Tipo di notifica (es. MAIL_NOT_PERMITTED)  
        message_id (str): ID del messaggio email
        text (str, optional): Testo aggiuntivo della notifica
        
    Returns:
        bool: True se l'inserimento è avvenuto con successo, False altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        # Prepara i dati da inserire
        notification_data = {
            "email": email,
            "type": notification_type,
            "message_id": message_id
        }
        
        # Aggiungi il testo se fornito
        if text:
            notification_data["text"] = text
        
        # Inserisci la notifica nel database
        response = supabase.table("notifications").insert(notification_data).execute()
        
        if not response.data:
            print(f"❌ [DB_CLIENT] Failed to insert notification for {email}")
            return False
        
        inserted_notification = response.data[0]
        notification_id = inserted_notification.get("notification_id")

        return True
        
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error inserting notification (sync) for {email}: {str(e)}")
        return False


def get_email_attachments_sync(message_id: str) -> list:
    """
    Recupera i file attachment associati a un message_id.
    Versione sincrona per i nodi del workflow.
    
    Args:
        message_id (str): ID del messaggio email
        
    Returns:
        list: Lista di attachment con file_name, file_path, mime_type, size_bytes
    """
    try:
        supabase = get_supabase_client()
        
        print(f"📎 [DB_CLIENT] Retrieving attachments for message_id: {message_id}")
        
        # Query per ottenere i file attachment
        response = supabase.table("email_attachments").select(
            "file_name, file_path, mime_type, size_bytes"
        ).eq("message_id", message_id).execute()
        
        if not response.data:
            print(f"⚠️ [DB_CLIENT] No attachments found for message_id: {message_id}")
            return []
        
        attachment_files = []
        for attachment_record in response.data:
            # Convert file path from /app/attachments to /automations/attachments
            original_path = attachment_record["file_path"]
            converted_path = original_path.replace("/app/attachments", "/automations/attachments")
            
            attachment_files.append({
                "file_name": attachment_record["file_name"],
                "file_path": converted_path,
                "mime_type": attachment_record.get("mime_type", ""),
                "size_bytes": attachment_record.get("size_bytes", 0)
            })
    
        
        print(f"✅ [DB_CLIENT] Retrieved {len(attachment_files)} attachments with converted paths")
        return attachment_files
        
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error retrieving attachments for message_id {message_id}: {str(e)}")
        return []


def get_calendar_service_data(service_id: str) -> Optional[Dict]:
    """
    Recupera dati del servizio calendario e subscription dal DB.
    
    Args:
        service_id: Service ID from subscription_services
        
    Returns:
        Dict con calendar_provider, access_token (decrypted), opening_hrs, working_days, appointment_duration
        None se non trovato
    """
    try:
        from ec_system.utils.utils import decrypt
        
        supabase = get_supabase_client()
        
        # Fetch subscription service data
        response_sub_ser = supabase.table("subscription_services").select(
            "subscription_id, calendar_provider, hashed_access_token"
        ).eq("service_id", service_id).execute()
        
        if not response_sub_ser.data:
            print(f"❌ [DB_CLIENT] No subscription service data found for service_id: {service_id}")
            return None
        
        data = response_sub_ser.data[0]
        calendar_provider = data.get("calendar_provider")
        hashed_access_token = data.get("hashed_access_token")
        subscription_id = data.get("subscription_id")
        
        if not hashed_access_token:
            print(f"❌ [DB_CLIENT] No hashed access token found")
            return None
        
        # Decrypt token
        access_token = decrypt(hashed_access_token, "token")
        if not access_token:
            print(f"❌ [DB_CLIENT] Failed to decrypt token")
            return None
        
        # Fetch subscription data
        response_sub = supabase.table("subscriptions").select(
            "business_hours, appointment_duration"
        ).eq("subscription_id", subscription_id).execute()
        
        if not response_sub.data:
            print(f"❌ [DB_CLIENT] No subscription data found for subscription_id: {subscription_id}")
            return None
        
        sub_data = response_sub.data[0]
        
        result = {
            "subscription_id": subscription_id,
            "calendar_provider": calendar_provider,
            "access_token": access_token,
            "business_hours": sub_data.get("business_hours"),
            "appointment_duration": sub_data.get("appointment_duration")
        }
        
        print(f"✅ [DB_CLIENT] Calendar service data retrieved for service_id: {service_id}")
        return result
        
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error retrieving calendar service data: {str(e)}")
        return None


def insert_scheduled_event(event_data: Dict) -> bool:
    """
    Inserisce un evento nella tabella scheduled_events.
    
    Args:
        event_data: Dizionario con i dati dell'evento (title, service_id, thread_id, event_type, event_code, created_by, created_at)
        
    Returns:
        bool: True se inserimento riuscito, False altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("scheduled_events").insert(event_data).execute()
        
        if response.data:
            print(f"✅ [DB_CLIENT] Event inserted with code: {event_data.get('event_code')}")
            return True
        else:
            print(f"❌ [DB_CLIENT] Failed to insert event")
            return False
            
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error inserting event: {e}")
        return False

def get_scheduled_event_by_code(event_code: str) -> Optional[Dict]:
    """
    Recupera un evento dalla tabella scheduled_events per un event_code specifico.
    
    Args:
        event_code: Event code per cui recuperare l'evento
        
    Returns:
        Dict: Dizionario con i dati dell'evento se trovato, None altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("scheduled_events").select("*").eq("event_code", event_code).execute()
        
        if response.data:
            return response.data[0]
        else:
            return None
            
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error retrieving event by code: {e}")
        return None

def check_event_code_exists(event_code: str) -> bool:
    """
    Verifica se un event_code esiste già nel database.
    
    Args:
        event_code: Event code da verificare
        
    Returns:
        bool: True se esiste, False altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("scheduled_events").select("event_code").eq("event_code", event_code).execute()
        
        return bool(response.data)
        
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error checking event code: {e}")
        return False

def delete_event_from_db(event_code: str):
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("scheduled_events").delete().eq("event_code", event_code).execute()
        
        if response.data:
            return True
        else:
            return False
            
    except Exception as e:
        return False


def save_ai_generated_email(email_data: Dict) -> bool:
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("ai_generated_emails").insert(email_data).execute()
        
        if response.data:
            print(f"✅ [DB_CLIENT] Email saved")
            return True
        else:
            print(f"❌ [DB_CLIENT] Failed to save email")
            return False
            
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error saving email: {e}")
        return False


def get_subscription_service_id_by_email(email: str) -> Optional[str]:
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("subscription_services").select("service_id").eq("email", email).execute()
        
        if response.data:
            return response.data[0].get("service_id")
        else:
            return None
            
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error getting service_id by email: {e}")
        return None


def update_thread(thread_id: str, thread_data: Dict) -> bool:
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("threads").update(thread_data).eq("thread_id", thread_id).execute()
        
        if response.data:
            print(f"✅ [DB_CLIENT] Thread updated for thread_id: {thread_id}")
            return True
        else:
            print(f"❌ [DB_CLIENT] Failed to update thread for thread_id: {thread_id}")
            return False
            
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error updating thread for thread_id: {e}")
        return False


def update_scheduled_event_provider_id(event_code: str, new_provider_event_id: str) -> bool:
    """
    Aggiorna il provider_event_id di un evento nella tabella scheduled_events.
    
    Args:
        event_code: Event code dell'evento da aggiornare
        new_provider_event_id: Nuovo provider event ID da salvare
        
    Returns:
        bool: True se aggiornamento riuscito, False altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("scheduled_events").update({
            "provider_event_id": new_provider_event_id
        }).eq("event_code", event_code).execute()
        
        if response.data:
            print(f"✅ [DB_CLIENT] Updated provider_event_id for event code: {event_code}")
            return True
        else:
            print(f"❌ [DB_CLIENT] Failed to update provider_event_id for event code: {event_code}")
            return False
            
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error updating provider_event_id: {e}")
        return False


def get_company_information_sync(box_email: str) -> Optional[str]:
    """
    Recupera le informazioni aziendali (campo 'information') dalla tabella subscription_services.
    Versione sincrona per i nodi del workflow.
    
    Args:
        box_email (str): Email della casella di posta
        
    Returns:
        str: Informazioni aziendali in formato markdown, None se non trovate o vuote
    """
    try:
        supabase = get_supabase_client()
        
        # Query per recuperare il campo information
        response = supabase.table("subscription_services") \
            .select("information") \
            .eq("email", box_email) \
            .eq("activated", True) \
            .execute()
        
        if not response.data or len(response.data) == 0:
            print(f"⚠️ [DB_CLIENT] No subscription found for box_email: {box_email}")
            return None
        
        company_info = response.data[0].get("information")
        
        # Verifica se information è vuoto o None
        if not company_info or company_info.strip() == "":
            print(f"⚠️ [DB_CLIENT] Company information is empty for box_email: {box_email}")
            return None
        
        print(f"✅ [DB_CLIENT] Company information retrieved successfully (length: {len(company_info)} chars)")
        return company_info
        
    except Exception as e:
        print(f"❌ [DB_CLIENT] Error retrieving company information: {str(e)}")
        return None


if __name__ == "__main__":
    # Test del modulo
    import asyncio
    
    async def test_module():
        print("🧪 Testing db_client module...")
        
        # Test connessione
        await test_database_connection()
        
        # Test configurazione utente (usa un email di test)
        test_email = "test@example.com"
        config = await get_user_configuration(test_email)
        
        if config:
            print(f"Config found: {config}")
            print(f"Config dict: {config.to_dict()}")
        else:
            print("No config found, using default")
            default_config = get_default_configuration()
            print(f"Default config: {default_config.to_dict()}")
    
    asyncio.run(test_module())