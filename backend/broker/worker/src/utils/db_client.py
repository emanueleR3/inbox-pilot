"""
Database client for broker worker.
Handles Supabase database connections and operations.
Based on the same pattern used in listeners.
"""

import os
from supabase import create_client, Client
from threading import Lock
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

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


def _normalize_datetime_value(value: Any) -> str:
    """Normalize various timestamp formats to ISO-8601 UTC string.

    Accepts:
    - epoch milliseconds/seconds (int/float or numeric string)
    - ISO-8601 strings (with or without timezone, including trailing Z)
    - RFC 2822 strings (email Date header)
    - datetime objects
    """
    now_utc = datetime.now(timezone.utc)
    if value is None or value == "":
        return now_utc.isoformat()

    dt: datetime
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:  # milliseconds
            ts /= 1000.0
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    elif isinstance(value, str):
        s = value.strip()
        if not s:
            return now_utc.isoformat()
        if s.isdigit():
            ts = float(s)
            if ts > 1e12:
                ts /= 1000.0
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                try:
                    dt = parsedate_to_datetime(s)
                except Exception:
                    return now_utc.isoformat()
    else:
        return now_utc.isoformat()

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


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

        # Idempotency: if we already saved this message_id, don't insert again.
        message_id = email_data.get("message_id")
        if message_id:
            existing = get_email_by_message_id(message_id)
            if existing and existing.get("email_id"):
                print(f"ℹ️ [DB] Email already exists for message_id={message_id} -> email_id: {existing.get('email_id')}")
                return existing.get("email_id")

        normalized_datetime = _normalize_datetime_value(email_data.get("datetime"))
        response_at_id = email_data.get("response_at_id")
        
        emails_data = {
            "thread_id": email_data.get("thread_id"),
            "message_id": email_data.get("message_id"),
            "response_at_id": response_at_id if isinstance(response_at_id, str) and response_at_id.lower() != "no" else None,
            "datetime": normalized_datetime,
            "body": email_data.get("body"),
            "service_id": email_data.get("service_id"),
            "outcome": email_data.get("outcome", "RECEIVED"),
            "ai_generated": email_data.get("ai_generated", False),
            "direction": email_data.get("direction", "INBOUND"),
            "has_attachment": email_data.get("has_attachment", False)
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


def find_ai_draft_for_thread(thread_id: str, response_at_id: str) -> Optional[Dict]:
    """
    Trova un draft AI esistente per un thread specifico che risponde a un messaggio specifico.
    Usato per identificare se una mail outbound corrisponde a un draft creato dal sistema AI.
    
    Args:
        thread_id: UUID del thread
        response_at_id: message_id del messaggio a cui si risponde
        
    Returns:
        Dict con i dati dell'email draft se trovata, None altrimenti
    """
    try:
        if not thread_id or not response_at_id:
            return None
        
        # Normalizza response_at_id
        if response_at_id.lower() == "no":
            return None
            
        supabase = get_supabase_client()
        
        # Cerca un draft AI per questo thread che risponde allo stesso messaggio
        response = supabase.table("emails").select("*").eq(
            "thread_id", thread_id
        ).eq(
            "response_at_id", response_at_id
        ).eq(
            "ai_generated", True
        ).eq(
            "outcome", "DRAFT"
        ).order(
            "datetime", desc=True
        ).limit(1).execute()
        
        if response.data:
            draft = response.data[0]
            print(f"🔍 [DB] Found AI draft for thread {thread_id}: email_id={draft.get('email_id')}, message_id={draft.get('message_id')}")
            return draft
        else:
            return None
            
    except Exception as e:
        print(f"❌ [DB] Error finding AI draft: {e}")
        return None


def update_draft_to_sent(email_id: str, new_message_id: str, new_datetime: str = None) -> bool:
    """
    Aggiorna un draft AI esistente quando l'utente lo invia manualmente.
    Cambia outcome da DRAFT a SENT e aggiorna il message_id con quello reale.
    
    Args:
        email_id: UUID del draft da aggiornare
        new_message_id: Nuovo message_id assegnato dal provider email
        new_datetime: Timestamp di invio (opzionale)
        
    Returns:
        bool: True se aggiornamento riuscito, False altrimenti
    """
    try:
        if not email_id or not new_message_id:
            return False
            
        supabase = get_supabase_client()
        
        update_data = {
            "message_id": new_message_id,
            "outcome": "SENT"
        }
        
        if new_datetime:
            update_data["datetime"] = _normalize_datetime_value(new_datetime)
        
        response = supabase.table("emails").update(update_data).eq("email_id", email_id).execute()
        
        if response.data:
            print(f"✅ [DB] Draft updated to SENT: email_id={email_id}, new_message_id={new_message_id}")
            return True
        else:
            print(f"❌ [DB] Failed to update draft to SENT for email_id: {email_id}")
            return False
            
    except Exception as e:
        print(f"❌ [DB] Error updating draft to SENT: {e}")
        return False


# ======================
# Threads helpers
# ======================

def get_thread_by_id(thread_id: str) -> Optional[Dict]:
    """Fetch a thread row by internal UUID thread_id."""
    try:
        if not thread_id:
            return None
        supabase = get_supabase_client()
        response = supabase.table("threads").select("*").eq("thread_id", thread_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"❌ [DB] Error getting thread by id: {e}")
        return None


def update_thread_status(thread_id: str, status: str) -> bool:
    """Update threads.status."""
    try:
        if not thread_id:
            return False
        supabase = get_supabase_client()
        response = supabase.table("threads").update({"status": status}).eq("thread_id", thread_id).execute()
        if response.data:
            print(f"✅ [DB] Thread status updated to '{status}' for thread {thread_id}")
            return True
        print(f"❌ [DB] Failed to update thread status for thread {thread_id}")
        return False
    except Exception as e:
        print(f"❌ [DB] Error updating thread status: {e}")
        return False


def update_thread_human_response(thread_id: str, human_response: bool) -> bool:
    """Update threads.human_response."""
    try:
        if not thread_id:
            return False
        supabase = get_supabase_client()
        response = supabase.table("threads").update({"human_response": bool(human_response)}).eq("thread_id", thread_id).execute()
        if response.data:
            print(f"✅ [DB] Thread human_response updated to '{bool(human_response)}' for thread {thread_id}")
            return True
        print(f"❌ [DB] Failed to update thread human_response for thread {thread_id}")
        return False
    except Exception as e:
        print(f"❌ [DB] Error updating thread human_response: {e}")
        return False


def append_email_id_to_history_internal(thread_id: str, email_id: str) -> bool:
    """Append an email UUID to threads.history_internal (idempotent)."""
    try:
        if not thread_id or not email_id:
            return False
        supabase = get_supabase_client()
        current = supabase.table("threads").select("history_internal").eq("thread_id", thread_id).execute()
        if not current.data:
            print(f"❌ [DB] Thread {thread_id} not found for history_internal update")
            return False
        history_internal = current.data[0].get("history_internal") or []
        if not isinstance(history_internal, list):
            history_internal = list(history_internal)
        if email_id in history_internal:
            return True
        history_internal.append(email_id)
        updated = supabase.table("threads").update({"history_internal": history_internal}).eq("thread_id", thread_id).execute()
        return bool(updated.data)
    except Exception as e:
        print(f"❌ [DB] Error updating history_internal: {e}")
        return False


def update_thread_history(thread_id: str, new_message_id: str) -> bool:
    """Append a message_id to threads.history (idempotent) and refresh last_message fields."""
    try:
        if not thread_id or not new_message_id:
            return False
        supabase = get_supabase_client()
        current = supabase.table("threads").select("history").eq("thread_id", thread_id).execute()
        if not current.data:
            print(f"❌ [DB] Thread {thread_id} not found for history update")
            return False
        history = current.data[0].get("history") or []
        if not isinstance(history, list):
            history = list(history)
        if new_message_id in history:
            return True
        history.append(new_message_id)
        update_data = {
            "history": history,
            "last_message_id": new_message_id,
            "last_message_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = supabase.table("threads").update(update_data).eq("thread_id", thread_id).execute()
        return bool(resp.data)
    except Exception as e:
        print(f"❌ [DB] Error updating thread history: {e}")
        return False


def update_thread_with_new_message(
    thread_id: str,
    message_id: str,
    message_timestamp: datetime,
    sender_email: str,
    cc_emails: list[str] | None = None,
    reply_to_id: str | None = None,
    email_id: str | None = None,
) -> bool:
    """Sync threads.history/history_internal and last_* fields for a new message."""
    try:
        if not thread_id or not message_id:
            return False
        supabase = get_supabase_client()
        current = supabase.table("threads").select("history,history_internal,cc_emails").eq("thread_id", thread_id).execute()
        if not current.data:
            print(f"❌ [DB] Thread {thread_id} not found for message sync")
            return False

        row = current.data[0]
        history = row.get("history") or []
        if not isinstance(history, list):
            history = list(history)
        history_internal = row.get("history_internal") or []
        if not isinstance(history_internal, list):
            history_internal = list(history_internal)
        existing_cc = row.get("cc_emails") or []
        if not isinstance(existing_cc, list):
            existing_cc = list(existing_cc)

        updated_history = list(history)
        if reply_to_id and isinstance(reply_to_id, str) and reply_to_id.lower() != "no" and reply_to_id not in updated_history:
            updated_history.append(reply_to_id)
        if message_id not in updated_history:
            updated_history.append(message_id)

        updated_history_internal = list(history_internal)
        if email_id and email_id not in updated_history_internal:
            updated_history_internal.append(email_id)

        updated_cc = list(existing_cc)
        if cc_emails:
            for cc in cc_emails:
                if cc and cc not in updated_cc:
                    updated_cc.append(cc)

        if message_timestamp is None:
            message_timestamp = datetime.now(timezone.utc)
        if message_timestamp.tzinfo is None:
            message_timestamp = message_timestamp.replace(tzinfo=timezone.utc)

        update_data = {
            "history": updated_history,
            "history_internal": updated_history_internal,
            "last_message_id": message_id,
            "last_message_at": message_timestamp.isoformat(),
            "last_sender_email": sender_email,
            "cc_emails": updated_cc,
        }
        resp = supabase.table("threads").update(update_data).eq("thread_id", thread_id).execute()
        return bool(resp.data)
    except Exception as e:
        print(f"❌ [DB] Error syncing thread with new message: {e}")
        return False