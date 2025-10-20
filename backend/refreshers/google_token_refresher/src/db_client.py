import os
from datetime import datetime, timedelta
from supabase import create_client, Client
from threading import Lock
from typing import List, Dict
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
                encryption_key_str = os.getenv("ENCRYPTION_KEY")
                if not encryption_key_str:
                    raise ValueError("ENCRYPTION_KEY non trovata nelle variabili d'ambiente")
                
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

async def get_tokens_expiring_soon(threshold_minutes=15) -> List[Dict]:
    """
    Ritorna i token Google che scadranno entro X minuti.
    
    Args:
        threshold_minutes (int): Minuti prima della scadenza per considerare un token "in scadenza"
        
    Returns:
        List[Dict]: Lista di token in scadenza nel formato richiesto dal token_refresher
    """
    try:
        supabase = get_supabase_client()
        
        # Calcola il timestamp di soglia
        threshold_time = datetime.utcnow() + timedelta(minutes=threshold_minutes)
        threshold_iso = threshold_time.isoformat() + "+00:00"
        
        # Query per ottenere tutti i token Google che scadranno presto
        # Filtriamo per:
        # - expiry_token non null (hanno token con scadenza)
        # - hashed_access_token e hashed_refresh_token non null (hanno token Google)
        # - expiry_token <= threshold_time (scadono presto)
        # - activated = true (account attivato)
        response = supabase.table("subscription_services").select("*").not_.is_("expiry_token", "null").not_.is_("hashed_access_token", "null").not_.is_("hashed_refresh_token", "null").lte("expiry_token", threshold_iso).eq("activated", True).execute()
        
        if not response.data:
            print(f"ℹ️ Nessun token Google in scadenza nei prossimi {threshold_minutes} minuti")
            return []
        
        expiring_tokens = []
        
        for record in response.data:
            try:
                # Decrittografa i token
                access_token = ""
                refresh_token = ""
                
                if record.get("hashed_access_token"):
                    access_token = _decrypt_token(record["hashed_access_token"])
                
                if record.get("hashed_refresh_token"):
                    refresh_token = _decrypt_token(record["hashed_refresh_token"])
                
                # Verifica che i token essenziali siano presenti
                if not refresh_token:
                    print(f"⚠️ Refresh token mancante per {record.get('email')}")
                    continue
                
                # Crea il dizionario nel formato richiesto dal token_refresher
                token_data = {
                    "email": record.get("email"),                  # Email dell'utente
                    "access_token": access_token,                  # Access token decrittato
                    "refresh_token": refresh_token,                # Refresh token decrittato
                    "expires_at": record.get("expiry_token"),      # Timestamp di scadenza
                    "subscription_id": record.get("subscription_id") # ID subscription per riferimento
                }
                
                expiring_tokens.append(token_data)
                
                # Parsing della data per il log
                expires_at = datetime.fromisoformat(record.get("expiry_token").replace("Z", "+00:00"))
                time_to_expiry = expires_at - datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
                minutes_to_expiry = int(time_to_expiry.total_seconds() / 60)
                
                print(f"⏰ Token in scadenza per {record.get('email')}: scade tra {minutes_to_expiry} minuti")
                
            except Exception as e:
                print(f"❌ Errore nella decrittazione/elaborazione token per {record.get('email')}: {str(e)}")
                continue
        
        print(f"📊 Totale token Google in scadenza: {len(expiring_tokens)}")
        return expiring_tokens
        
    except Exception as e:
        print(f"❌ Errore nel recupero dei token in scadenza: {str(e)}")
        return []

async def update_user_tokens(email: str, access_token: str, expires_in: int) -> bool:
    """
    Aggiorna i token dell'utente nel database.
    Il nuovo access token viene automaticamente crittografato prima del salvataggio.
    
    Args:
        user_id (str): ID del servizio (service_id)
        access_token (str): Nuovo access token (verrà crittografato)
        expires_in (int): Durata di validità del token in secondi
        
    Returns:
        bool: True se l'aggiornamento è avvenuto con successo, False altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        # Calcola la nuova data di scadenza
        new_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        new_expiry_iso = new_expiry.isoformat() + "+00:00"
        
        # Crittografa il nuovo access token
        encrypted_access_token = _encrypt_token(access_token)
        
        # Aggiorna il record nel database
        update_data = {
            "hashed_access_token": encrypted_access_token,
            "expiry_token": new_expiry_iso
        }
        
        response = supabase.table("subscription_services").update(update_data).eq("email", email).execute()
        
        if not response.data:
            print(f"❌ Nessun record trovato per email: {email}")
            return False
        
        updated_record = response.data[0]
        email = updated_record.get("email", "unknown")
        
        print(f"✅ Token aggiornato con successo per {email}")
        print(f"   Nuova scadenza: {new_expiry.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nell'aggiornamento dei token per email: {email}: {str(e)}")
        return False