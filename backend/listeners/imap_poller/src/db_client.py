
import os
from supabase import create_client, Client
from threading import Lock
from typing import List, Dict
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from src.utils.logger import log_error, log_info
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
                encryption_key_str = os.getenv("ENCRYPTION_KEY_PASS")
                if not encryption_key_str:
                    raise ValueError("ENCRYPTION_KEY non trovata nelle variabili d'ambiente")
                
                # Genera la chiave Fernet dalla chiave base (stesso metodo del DAO)
                encryption_key = encryption_key_str.encode()
                key_hash = hashlib.sha256(encryption_key).digest()
                fernet_key = base64.urlsafe_b64encode(key_hash)
                _cipher = Fernet(fernet_key)
    return _cipher

def _decrypt_password(encrypted_password: str) -> str:
    """
    Decifra una password cifrata.
    """
    if not encrypted_password:
        return ""
    cipher = _get_cipher()
    return cipher.decrypt(encrypted_password.encode()).decode()

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

async def get_all_imap_accounts() -> List[Dict]:
    """
    Recupera tutte le caselle IMAP da monitorare dal database Supabase.
    Ritorna solo gli account che hanno configurazione IMAP/SMTP completa e sono attivati.
    
    Returns:
        List[Dict]: Lista di dizionari con le configurazioni IMAP nel formato richiesto dal poller
    """
    try:
        supabase = get_supabase_client()
        
        # Query per ottenere tutti gli account con configurazione IMAP/SMTP
        # Filtriamo per:
        # - imap_server e smtp_server non null (hanno configurazione IMAP/SMTP)
        # - activated = true (account attivato)
        # - config_completed = true (configurazione completata)
        response = supabase.table("subscription_services").select("*").not_.is_("imap_server", "null").not_.is_("smtp_server", "null").eq("activated", True).eq("config_completed", True).execute()
        
        if not response.data:
            log_info("Nessun account IMAP configurato e attivato trovato")
            return []
        
        imap_accounts = []
        
        for account in response.data:
            try:
                # Decritta la password
                decrypted_password = ""
                if account.get("hashed_password"):
                    decrypted_password = _decrypt_password(account["hashed_password"])
                
                # Crea il dizionario nel formato richiesto dal poller
                imap_account = {
                    "imap_host": account.get("imap_server"),           # Nome corretto per il poller
                    "imap_port": account.get("imap_port", 993),        # Default IMAP SSL port
                    "email": account.get("email"),                     # Email dell'account
                    "password": decrypted_password,                    # Password decriptata
                    "use_ssl": True,                                   # Default SSL attivo per sicurezza
                    "smtp_server": account.get("smtp_server"),        # Info aggiuntive per eventuale uso
                    "smtp_port": account.get("smtp_port", 587),       # Default SMTP port
                    "subscription_id": account.get("subscription_id") # ID subscription per riferimento
                }
                
                # Verifica che i campi essenziali siano presenti
                if imap_account["imap_host"] and imap_account["email"] and decrypted_password:
                    imap_accounts.append(imap_account)
                    log_info(f"Account IMAP configurato: {imap_account['email']} -> {imap_account['imap_host']}:{imap_account['imap_port']}")
                else:
                    log_error(f"⚠️ Account IMAP incompleto per {account.get('email')}: mancano campi essenziali")
                    
            except Exception as e:
                log_error(f"❌ Errore nella decrittazione/configurazione account {account.get('email')}: {str(e)}")
                continue
        
        log_info(f"📊 Totale account IMAP configurati: {len(imap_accounts)}")
        return imap_accounts
        
    except Exception as e:
        log_error(f"❌ Errore nel recupero degli account IMAP: {str(e)}")
        return []

def get_last_sent_message_info(email: str) -> Dict:
    """
    Recupera info sull'ultimo messaggio inviato processato per un account IMAP.
    
    Args:
        email: Email dell'account
        
    Returns:
        Dict con 'message_id' e 'timestamp' dell'ultimo messaggio processato
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("subscription_services").select(
            "last_sent_message_id, last_sent_timestamp"
        ).eq("email", email).eq("email_provider", "imap").single().execute()
        
        if response.data:
            return {
                "message_id": response.data.get("last_sent_message_id"),
                "timestamp": response.data.get("last_sent_timestamp")
            }
        
        return {"message_id": None, "timestamp": None}
        
    except Exception as e:
        log_error(f"❌ Errore nel recupero ultimo messaggio inviato per {email}: {str(e)}")
        return {"message_id": None, "timestamp": None}

def update_last_sent_message_info(email: str, message_id: str, timestamp: str):
    """
    Aggiorna le info dell'ultimo messaggio inviato processato per un account IMAP.
    
    Args:
        email: Email dell'account
        message_id: ID del messaggio più recente processato
        timestamp: Timestamp ISO del messaggio più recente
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("subscription_services").update({
            "last_sent_message_id": message_id,
            "last_sent_timestamp": timestamp
        }).eq("email", email).eq("email_provider", "imap").execute()
        
        if response.data:
            log_info(f"✅ Aggiornato ultimo messaggio inviato per {email}: {message_id} (timestamp: {timestamp})")
        else:
            log_error(f"❌ Errore nell'aggiornamento ultimo messaggio inviato per {email}")
            
    except Exception as e:
        log_error(f"❌ Errore nell'aggiornamento ultimo messaggio inviato per {email}: {str(e)}")
