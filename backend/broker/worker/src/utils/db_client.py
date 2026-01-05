"""
Database client for broker worker.
Handles Supabase database connections and operations.
Based on the same pattern used in listeners.
"""

import os
from supabase import create_client, Client
from threading import Lock
from typing import Dict, Optional
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64
import hashlib

# Carica le variabili d'ambiente
load_dotenv()

# Client Supabase singleton
_supabase_client: Client | None = None
_client_lock = Lock()

# Chiave di cifratura
_cipher = None
_cipher_lock = Lock()

def _get_cipher():
    """
    Ottiene il cipher Fernet per la crittografia/decrittografia dei token.
    Utilizza il pattern singleton con thread safety.
    """
    global _cipher
    if _cipher is None:
        with _cipher_lock:
            if _cipher is None:  # double-checked locking
                encryption_key_str = os.getenv("ENCRYPTION_KEY_TOKEN")
                if not encryption_key_str:
                    raise ValueError("ENCRYPTION_KEY_TOKEN non trovata nelle variabili d'ambiente")
                
                # Genera la chiave Fernet dalla chiave base (stesso metodo del DAO)
                encryption_key = encryption_key_str.encode()
                key_hash = hashlib.sha256(encryption_key).digest()
                fernet_key = base64.urlsafe_b64encode(key_hash)
                _cipher = Fernet(fernet_key)
    return _cipher

def _encrypt_token(token: str) -> str:
    """
    Cifra un token usando Fernet (AES-256).
    """
    if not token:
        return ""
    cipher = _get_cipher()
    return cipher.encrypt(token.encode()).decode()

def _decrypt_token(encrypted_token: str) -> str:
    """
    Decifra un token cifrato.
    """
    if not encrypted_token:
        return ""
    cipher = _get_cipher()
    return cipher.decrypt(encrypted_token.encode()).decode()

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

def get_user_subscription_data(email: str) -> Dict:
    """
    Recupera i dati di subscription dell'utente dal database.
    
    Args:
        email (str): Email dell'utente
        
    Returns:
        dict: Dizionario contenente i dati dell'utente
        
    Raises:
        Exception: Se l'utente non viene trovato o si verifica un errore
    """
    try:
        supabase = get_supabase_client()
        
        # Query per ottenere i dati dell'utente dalla tabella subscription_services
        response = supabase.table("subscription_services").select("*").eq("email", email.lower()).execute()
        
        if not response.data:
            raise Exception(f"Utente con email {email} non trovato")
        
        user_data = response.data[0]
        
        return {
            "email": user_data.get("email"),
            "subscription_id": user_data.get("subscription_id"),
            "email_provider": user_data.get("email_provider"),
            "activated": user_data.get("activated", False),
            "config_completed": user_data.get("config_completed", False)
        }
        
    except Exception as e:
        print(f"❌ Errore nel recupero dei dati subscription per {email}: {str(e)}")
        raise

def get_gmail_credentials(user_email: str) -> Dict:
    """
    Recupera le credenziali Gmail dell'utente dal database Supabase.
    I token vengono automaticamente decrittati.
    
    Args:
        user_email (str): Email dell'utente
        
    Returns:
        dict: Dizionario contenente le credenziali dell'utente decrittate
        
    Raises:
        Exception: Se l'utente non viene trovato o si verifica un errore
    """
    try:
        supabase = get_supabase_client()
        
        # Query per ottenere le credenziali dell'utente dalla tabella subscription_services
        response = supabase.table("subscription_services").select("*").eq("email", user_email.lower()).execute()
        
        if not response.data:
            raise Exception(f"Gmail user {user_email} not found in database")
        
        user_data = response.data[0]
        
        # Decrittare i token se presenti
        access_token = ""
        refresh_token = ""
        
        if user_data.get("hashed_access_token"):
            access_token = _decrypt_token(user_data["hashed_access_token"])
        
        if user_data.get("hashed_refresh_token"):
            refresh_token = _decrypt_token(user_data["hashed_refresh_token"])
        
        # Ritorna le credenziali necessarie per Gmail API con i token decrittati
        return {
            "email": user_data.get("email"),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expiry": user_data.get("expiry_token"),
            "history_id": user_data.get("history_id"),
            "subscription_id": user_data.get("subscription_id"),
            "oauth_user_id": user_data.get("oauth_user_id")
        }
        
    except Exception as e:
        print(f"❌ [DB] Error retrieving Gmail credentials for {user_email}: {str(e)}")
        raise

def get_microsoft_credentials(user_email: str) -> Dict:
    """
    Recupera le credenziali Microsoft dell'utente dal database Supabase.
    I token vengono automaticamente decrittati.
    
    Args:
        user_email (str): Email dell'utente
        
    Returns:
        dict: Dizionario contenente le credenziali dell'utente decrittate
        
    Raises:
        Exception: Se l'utente non viene trovato o si verifica un errore
    """
    try:
        supabase = get_supabase_client()
        
        # Query per ottenere le credenziali dell'utente dalla tabella subscription_services
        response = supabase.table("subscription_services").select("*").eq("email", user_email.lower()).execute()
        
        if not response.data:
            raise Exception(f"Microsoft user {user_email} not found in database")
        
        user_data = response.data[0]
        
        # Decrittare i token se presenti
        access_token = ""
        refresh_token = ""
        
        if user_data.get("hashed_access_token"):
            access_token = _decrypt_token(user_data["hashed_access_token"])
        
        if user_data.get("hashed_refresh_token"):
            refresh_token = _decrypt_token(user_data["hashed_refresh_token"])
        
        # Ritorna le credenziali necessarie per Microsoft Graph API con i token decrittati
        return {
            "email": user_data.get("email"),
            "oauth_user_id": user_data.get("oauth_user_id"),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expiry": user_data.get("expiry_token"),
            "subscription_id": user_data.get("subscription_id"),
            "microsoft_subscription_id_inbound": user_data.get("microsoft_subscription_id_inbound"),
            "microsoft_subscription_id_outbound": user_data.get("microsoft_subscription_id_outbound"),
            "microsoft_expiration_datetime_inbound": user_data.get("microsoft_expiration_datetime_inbound"),
            "microsoft_expiration_datetime_outbound": user_data.get("microsoft_expiration_datetime_outbound")
        }
        
    except Exception as e:
        print(f"❌ [DB] Error retrieving Microsoft credentials for {user_email}: {str(e)}")
        raise

def get_imap_credentials(user_email: str) -> Dict:
    """
    Recupera le credenziali IMAP dell'utente dal database Supabase.
    Le password vengono automaticamente decrittate.
    
    Args:
        user_email (str): Email dell'utente
        
    Returns:
        dict: Dizionario contenente le credenziali IMAP decrittate
        
    Raises:
        Exception: Se l'utente non viene trovato o si verifica un errore
    """
    try:
        # Per IMAP usiamo una chiave di crittografia diversa
        encryption_key_str = os.getenv("ENCRYPTION_KEY_PASS")
        if not encryption_key_str:
            raise ValueError("ENCRYPTION_KEY_PASS non trovata nelle variabili d'ambiente")
        
        # Genera la chiave Fernet per le password IMAP
        encryption_key = encryption_key_str.encode()
        key_hash = hashlib.sha256(encryption_key).digest()
        fernet_key = base64.urlsafe_b64encode(key_hash)
        cipher = Fernet(fernet_key)
        
        supabase = get_supabase_client()
        
        # Query per ottenere le credenziali IMAP dell'utente
        response = supabase.table("subscription_services").select("*").eq("email", user_email.lower()).not_.is_("imap_server", "null").execute()
        
        if not response.data:
            raise Exception(f"IMAP user {user_email} not found in database")
        
        user_data = response.data[0]
        
        # Decrittare la password se presente
        password = ""
        if user_data.get("hashed_password"):
            password = cipher.decrypt(user_data["hashed_password"].encode()).decode()
        
        # Ritorna le credenziali necessarie per IMAP
        return {
            "email": user_data.get("email"),
            "password": password,
            "imap_server": user_data.get("imap_server"),
            "imap_port": user_data.get("imap_port", 993),
            "smtp_server": user_data.get("smtp_server"),
            "smtp_port": user_data.get("smtp_port", 587),
            "subscription_id": user_data.get("subscription_id"),
            "use_ssl": True
        }
        
    except Exception as e:
        print(f"❌ [DB] Error retrieving IMAP credentials for {user_email}: {str(e)}")
        raise

def get_user_provider(user_email: str) -> Optional[str]:
    """
    Determina il provider email dell'utente (gmail, microsoft, imap).
    
    Args:
        user_email (str): Email dell'utente
        
    Returns:
        str: Provider dell'utente ("gmail", "microsoft", "imap") o None se non trovato
    """
    try:
        supabase = get_supabase_client()
        
        # Query per ottenere il provider dell'utente
        response = supabase.table("subscription_services").select("email_provider, imap_server").eq("email", user_email.lower()).execute()
        
        if not response.data:
            return None
        
        user_data = response.data[0]
        provider = user_data.get("email_provider")
        
        # Se il provider non è definito ma ha configurazione IMAP, è IMAP
        if not provider and user_data.get("imap_server"):
            return "imap"
        
        return provider
        
    except Exception as e:
        print(f"❌ [DB] Error determining provider for {user_email}: {str(e)}")
        return None


def get_service_id_by_email(email: str) -> Optional[str]:
    """
    Recupera il service_id per un'email dalla tabella subscription_services.
    
    Args:
        email: Email address to lookup
        
    Returns:
        service_id (UUID) se trovato, None altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("subscription_services").select("service_id").eq("email", email.lower()).execute()
        
        if response.data:
            return response.data[0].get("service_id")
        else:
            return None
            
    except Exception as e:
        print(f"❌ [DB] Error getting service_id for {email}: {e}")
        return None


def save_email(email_data: Dict) -> Optional[str]:
    """
    Salva una email nella tabella emails.
    
    Args:
        email_data: Dizionario con i dati dell'email:
            - thread_id: UUID del thread
            - message_id: ID del messaggio
            - response_at_id: In-Reply-To message ID
            - datetime: Timestamp dell'email
            - body: Corpo dell'email
            - service_id: UUID del servizio
            - outcome: Status dell'email (RECEIVED, SENT, etc.)
            - direction: INBOUND o OUTBOUND
            - has_attachment: Se ha allegati
            - ai_generated: Se generata da AI (default False)
            
    Returns:
        str: email_id se inserimento riuscito, None altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        # Cerca written_after_id basandosi su response_at_id
        response_at_id = email_data.get("response_at_id")
        written_after_id = None
        if response_at_id and response_at_id.lower() != "no":
            written_after = get_email_by_message_id(response_at_id)
            if written_after:
                written_after_id = written_after.get("email_id")
        
        emails_data = {
            "thread_id": email_data.get("thread_id"),
            "message_id": email_data.get("message_id"),
            "response_at_id": email_data.get("response_at_id") if email_data.get("response_at_id", "").lower() != "no" else None,
            "datetime": email_data.get("datetime"),
            "body": email_data.get("body"),
            "service_id": email_data.get("service_id"),
            "outcome": email_data.get("outcome", "RECEIVED"),
            "ai_generated": email_data.get("ai_generated", False),
            "direction": email_data.get("direction", "INBOUND"),
            "has_attachment": email_data.get("has_attachment", False),
            "written_after_id": written_after_id
        }
        
        # Rimuovi valori None
        emails_data = {k: v for k, v in emails_data.items() if v is not None}
        
        response = supabase.table("emails").insert(emails_data).execute()
        
        if response.data:
            email_id = response.data[0].get("email_id")
            direction = email_data.get("direction", "INBOUND")
            print(f"✅ [DB] {direction} email saved with email_id: {email_id}")
            return email_id
        else:
            print(f"❌ [DB] Failed to save email")
            return None
            
    except Exception as e:
        print(f"❌ [DB] Error saving email: {e}")
        return None


def get_email_by_message_id(message_id: str) -> Optional[Dict]:
    """
    Recupera una email dalla tabella emails per message_id.
    
    Args:
        message_id: ID del messaggio da cercare
        
    Returns:
        Dict con i dati dell'email se trovata, None altrimenti
    """
    try:
        if not message_id:
            return None
            
        supabase = get_supabase_client()
        
        response = supabase.table("emails").select("*").eq("message_id", message_id).execute()
        
        if response.data:
            return response.data[0]
        else:
            return None
            
    except Exception as e:
        print(f"❌ [DB] Error getting email by message_id: {e}")
        return None


def get_email_by_id(email_id: str) -> Optional[Dict]:
    """
    Recupera una email dalla tabella emails per email_id.
    
    Args:
        email_id: UUID dell'email da cercare
        
    Returns:
        Dict con i dati dell'email se trovata, None altrimenti
    """
    try:
        if not email_id:
            return None
            
        supabase = get_supabase_client()
        
        response = supabase.table("emails").select("*").eq("email_id", email_id).execute()
        
        if response.data:
            return response.data[0]
        else:
            return None
            
    except Exception as e:
        print(f"❌ [DB] Error getting email by email_id: {e}")
        return None