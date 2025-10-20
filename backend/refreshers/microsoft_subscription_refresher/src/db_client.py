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

async def get_subscriptions_expiring_soon(threshold_hours=12) -> List[Dict]:
    """
    Ritorna le subscription Microsoft che scadranno entro X ore.
    
    Args:
        threshold_hours (int): Ore prima della scadenza per considerare una subscription "in scadenza"
        
    Returns:
        List[Dict]: Lista di subscription in scadenza nel formato richiesto dal subscription_refresher
    """
    try:
        supabase = get_supabase_client()
        
        # Calcola il timestamp di soglia
        threshold_time = datetime.utcnow() + timedelta(hours=threshold_hours)
        threshold_iso = threshold_time.isoformat() + "+00:00"
        
        # Query per ottenere tutte le subscription Microsoft che scadranno presto
        # Filtriamo per:
        # - microsoft_subscription_id non null (hanno subscription Microsoft)
        # - microsoft_expiration_datetime non null (hanno data di scadenza)
        # - microsoft_expiration_datetime <= threshold_time (scadono presto)
        # - hashed_access_token non null (hanno token di accesso)
        # - activated = true (account attivato)
        response = supabase.table("subscription_services").select("*").not_.is_("microsoft_subscription_id", "null").not_.is_("microsoft_expiration_datetime", "null").not_.is_("hashed_access_token", "null").lte("microsoft_expiration_datetime", threshold_iso).eq("activated", True).execute()
        
        if not response.data:
            print(f"ℹ️ Nessuna subscription Microsoft in scadenza nelle prossime {threshold_hours} ore")
            return []
        
        expiring_subscriptions = []
        
        for record in response.data:
            try:
                # Decrittografa l'access token
                access_token = ""
                
                if record.get("hashed_access_token"):
                    access_token = _decrypt_token(record["hashed_access_token"])
                
                # Verifica che i campi essenziali siano presenti
                if not access_token or not record.get("microsoft_subscription_id"):
                    print(f"⚠️ Dati essenziali mancanti per {record.get('email')}")
                    continue
                
                # Crea il dizionario nel formato richiesto dal subscription_refresher
                subscription_data = {
                    "subscription_id": record.get("microsoft_subscription_id"),    # Microsoft subscription ID
                    "access_token": access_token,                                  # Access token decrittato
                    "expirationDateTime": record.get("microsoft_expiration_datetime"), # Data scadenza subscription
                    "email": record.get("email"),                                  # Email utente (per riferimento)
                    "service_id": record.get("service_id"),                       # ID del servizio (per aggiornamenti)
                    "user_subscription_id": record.get("subscription_id")         # ID subscription utente
                }
                
                expiring_subscriptions.append(subscription_data)
                
                # Parsing della data per il log
                expires_at = datetime.fromisoformat(record.get("microsoft_expiration_datetime").replace("Z", "+00:00"))
                time_to_expiry = expires_at - datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
                hours_to_expiry = time_to_expiry.total_seconds() / 3600
                
                print(f"⏰ Subscription Microsoft in scadenza per {record.get('email')}: scade tra {hours_to_expiry:.1f} ore")
                print(f"   Subscription ID: {record.get('microsoft_subscription_id')}")
                
            except Exception as e:
                print(f"❌ Errore nella decrittazione/elaborazione subscription per {record.get('email')}: {str(e)}")
                continue
        
        print(f"📊 Totale subscription Microsoft in scadenza: {len(expiring_subscriptions)}")
        return expiring_subscriptions
        
    except Exception as e:
        print(f"❌ Errore nel recupero delle subscription in scadenza: {str(e)}")
        return []

async def update_subscription_expiration(subscription_id: str, new_expiration: str) -> bool:
    """
    Aggiorna nel database la nuova data di scadenza per una subscription Microsoft.
    
    Args:
        subscription_id (str): Microsoft subscription ID
        new_expiration (str): Nuova data di scadenza in formato ISO
        
    Returns:
        bool: True se l'aggiornamento è avvenuto con successo, False altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        # Normalizza la data di scadenza (assicurati che sia in formato ISO corretto)
        if new_expiration.endswith('Z'):
            normalized_expiration = new_expiration.replace('Z', '+00:00')
        elif not new_expiration.endswith('+00:00') and not new_expiration.endswith('-'):
            normalized_expiration = new_expiration + "+00:00"
        else:
            normalized_expiration = new_expiration
        
        # Verifica che la data sia valida
        try:
            datetime.fromisoformat(normalized_expiration)
        except ValueError:
            print(f"❌ Formato data non valido per subscription {subscription_id}: {new_expiration}")
            return False
        
        # Aggiorna il record nel database
        update_data = {
            "microsoft_expiration_datetime": normalized_expiration
        }
        
        response = supabase.table("subscription_services").update(update_data).eq("microsoft_subscription_id", subscription_id).execute()
        
        if not response.data:
            print(f"❌ Nessun record trovato per Microsoft subscription ID: {subscription_id}")
            return False
        
        updated_record = response.data[0]
        email = updated_record.get("email", "unknown")
        
        # Parsing della nuova data per il log
        new_expiry_dt = datetime.fromisoformat(normalized_expiration)
        
        print(f"✅ Subscription Microsoft aggiornata con successo per {email}")
        print(f"   Subscription ID: {subscription_id}")
        print(f"   Nuova scadenza: {new_expiry_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nell'aggiornamento della subscription {subscription_id}: {str(e)}")
        return False

