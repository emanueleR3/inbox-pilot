import os
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
from threading import Lock
from typing import List, Dict
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64
import hashlib
from src.utils.logger import Logger

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

async def get_subscriptions_expiring_soon(threshold_minutes=15) -> List[Dict]:
    """
    Ritorna le subscription Microsoft (inbound e outbound) che scadranno entro X minuti.
    Restituisce sia le subscription inbound che outbound separatamente.
    
    Args:
        threshold_minutes (int): Minuti prima della scadenza per considerare una subscription "in scadenza"
        
    Returns:
        List[Dict]: Lista di subscription in scadenza con tipo (inbound/outbound)
    """
    try:
        supabase = get_supabase_client()
        
        # Calcola il timestamp di soglia (timezone-aware per UTC)
        threshold_time = datetime.now(timezone.utc) + timedelta(minutes=threshold_minutes)
        threshold_iso = threshold_time.isoformat().replace("+00:00", "Z")
        
        # Query per ottenere tutte le subscription Microsoft attive
        response = supabase.table("subscription_services").select("*").not_.is_("hashed_access_token", "null").eq("activated", True).eq("email_provider", "microsoft").execute()
        
        if not response.data:
            Logger.log_info("### MICROSOFT SUBSCRIPTION ⏰✅ Nessuna subscription Microsoft attiva trovata.")
            return []
        
        expiring_subscriptions = []
        
        for record in response.data:
            try:
                # Decrittografa l'access token
                access_token = ""
                if record.get("hashed_access_token"):
                    access_token = _decrypt_token(record["hashed_access_token"])
                
                if not access_token:
                    Logger.log_error(f"### MICROSOFT SUBSCRIPTION ⚠️ Access token mancante per {record.get('email')}")
                    continue
                
                email = record.get("email")
                user_subscription_id = record.get("subscription_id")
                
                # Controlla subscription inbound
                inbound_sub_id = record.get("microsoft_subscription_id_inbound")
                inbound_expiry = record.get("microsoft_expiration_datetime_inbound")
                
                if inbound_sub_id and inbound_expiry:
                    # Verifica se la subscription inbound è in scadenza
                    expiry_dt = datetime.fromisoformat(inbound_expiry.replace("Z", "+00:00"))
                    if expiry_dt <= threshold_time:
                        expiring_subscriptions.append({
                            "subscription_id": inbound_sub_id,
                            "subscription_type": "inbound",
                            "access_token": access_token,
                            "expirationDateTime": inbound_expiry,
                            "email": email,
                            "service_id": record.get("service_id"),
                            "user_subscription_id": user_subscription_id
                        })
                        
                        hours_to_expiry = (expiry_dt - datetime.now(timezone.utc)).total_seconds() / 3600
                        Logger.log_info(f"### MICROSOFT SUBSCRIPTION ⏰ 📥 Subscription INBOUND (Inbox) in scadenza per {email}: scade tra {hours_to_expiry:.1f} ore")
                        Logger.log_info(f"   🆔 Subscription ID: {inbound_sub_id}")
                        Logger.log_info(f"   📅 Scadenza: {expiry_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                
                # Controlla subscription outbound
                outbound_sub_id = record.get("microsoft_subscription_id_outbound")
                outbound_expiry = record.get("microsoft_expiration_datetime_outbound")
                
                if outbound_sub_id and outbound_expiry:
                    # Verifica se la subscription outbound è in scadenza
                    expiry_dt = datetime.fromisoformat(outbound_expiry.replace("Z", "+00:00"))
                    if expiry_dt <= threshold_time:
                        expiring_subscriptions.append({
                            "subscription_id": outbound_sub_id,
                            "subscription_type": "outbound",
                            "access_token": access_token,
                            "expirationDateTime": outbound_expiry,
                            "email": email,
                            "service_id": record.get("service_id"),
                            "user_subscription_id": user_subscription_id
                        })
                        
                        hours_to_expiry = (expiry_dt - datetime.now(timezone.utc)).total_seconds() / 3600
                        Logger.log_info(f"### MICROSOFT SUBSCRIPTION ⏰ 📤 Subscription OUTBOUND (SentItems) in scadenza per {email}: scade tra {hours_to_expiry:.1f} ore")
                        Logger.log_info(f"   🆔 Subscription ID: {outbound_sub_id}")
                        Logger.log_info(f"   📅 Scadenza: {expiry_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                
            except Exception as e:
                Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore nel processamento delle subscription per {record.get('email')}: {str(e)}")
                continue
        
        Logger.log_info(f"### MICROSOFT SUBSCRIPTION 📊 Totale subscription in scadenza: {len(expiring_subscriptions)}")
        if expiring_subscriptions:
            inbound_count = len([s for s in expiring_subscriptions if s.get('subscription_type') == 'inbound'])
            outbound_count = len([s for s in expiring_subscriptions if s.get('subscription_type') == 'outbound'])
            Logger.log_info(f"   📥 INBOUND (Inbox): {inbound_count}")
            Logger.log_info(f"   📤 OUTBOUND (SentItems): {outbound_count}")
        return expiring_subscriptions
        
    except Exception as e:
        Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore nel recupero delle subscription in scadenza: {str(e)}")
        return []

async def update_subscription_expiration(subscription_id: str, new_expiration: str, subscription_type: str = "inbound") -> bool:
    """
    Aggiorna nel database la nuova data di scadenza per una subscription Microsoft.
    Supporta sia subscription inbound che outbound.
    
    Args:
        subscription_id (str): Microsoft subscription ID
        new_expiration (str): Nuova data di scadenza in formato ISO
        subscription_type (str): Tipo di subscription ("inbound" o "outbound")
        
    Returns:
        bool: True se l'aggiornamento è avvenuto con successo, False altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        # Normalizza la data di scadenza
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
            Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Formato data non valido per subscription {subscription_id}: {new_expiration}")
            return False
        
        # Determina il campo da aggiornare in base al tipo di subscription
        if subscription_type == "inbound":
            field_subscription_id = "microsoft_subscription_id_inbound"
            field_expiration = "microsoft_expiration_datetime_inbound"
        elif subscription_type == "outbound":
            field_subscription_id = "microsoft_subscription_id_outbound"
            field_expiration = "microsoft_expiration_datetime_outbound"
        else:
            Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Tipo di subscription non valido: {subscription_type}")
            return False
        
        # Aggiorna il record nel database
        update_data = {
            field_expiration: normalized_expiration
        }
        
        response = supabase.table("subscription_services").update(update_data).eq(field_subscription_id, subscription_id).execute()
        
        if not response.data:
            Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Nessun record trovato per subscription {subscription_type} ID: {subscription_id}")
            return False
        
        updated_record = response.data[0]
        email = updated_record.get("email", "unknown")
        
        # Parsing della nuova data per il log
        new_expiry_dt = datetime.fromisoformat(normalized_expiration)
        
        # Emoji specifici per tipo di subscription
        type_emoji = "📥" if subscription_type == "inbound" else "📤"
        folder_type = "Inbox" if subscription_type == "inbound" else "SentItems"
        
        Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ {type_emoji} Subscription {subscription_type.upper()} ({folder_type}) aggiornata con successo per {email}.")
        Logger.log_info(f"   🆔 Subscription ID: {subscription_id}")
        Logger.log_info(f"   📅 Nuova scadenza: {new_expiry_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return True
        
    except Exception as e:
        Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore nell'aggiornamento della subscription {subscription_type} {subscription_id}: {str(e)}")
        return False

