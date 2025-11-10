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