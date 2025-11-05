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

async def get_user_credentials_inbound(microsoft_subscription_id_inbound: str) -> Dict:
    """
    Recupera le credenziali dell'utente Microsoft dal database Supabase usando il microsoft_subscription_id_inbound.
    I token vengono automaticamente decrittati.
    
    Args:
        microsoft_subscription_id_inbound (str): ID della subscription Microsoft inbound
        
    Returns:
        dict: Dizionario contenente le credenziali dell'utente decrittate
        
    Raises:
        Exception: Se l'utente non viene trovato o si verifica un errore
    """
    try:
        supabase = get_supabase_client()
        
        # Query per ottenere le credenziali dell'utente dalla tabella subscription_services
        # Cerchiamo per microsoft_subscription_id_inbound
        response = supabase.table("subscription_services").select("*").eq("microsoft_subscription_id_inbound", microsoft_subscription_id_inbound).execute()
        
        if not response.data:
            raise Exception(f"Utente con microsoft_subscription_id_inbound {microsoft_subscription_id_inbound} non trovato")
        
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
            "microsoft_expiration_datetime_inbound": user_data.get("microsoft_expiration_datetime_inbound")
        }
        
    except Exception as e:
        print(f"Errore nel recupero delle credenziali inbound per subscription_id {microsoft_subscription_id_inbound}: {str(e)}")
        raise

async def get_user_credentials_outbound(microsoft_subscription_id_outbound: str) -> Dict:
    """
    Recupera le credenziali dell'utente Microsoft dal database Supabase usando il microsoft_subscription_id_outbound.
    I token vengono automaticamente decrittati.
    
    Args:
        microsoft_subscription_id_outbound (str): ID della subscription Microsoft outbound
        
    Returns:
        dict: Dizionario contenente le credenziali dell'utente decrittate
        
    Raises:
        Exception: Se l'utente non viene trovato o si verifica un errore
    """
    try:
        supabase = get_supabase_client()
        
        # Query per ottenere le credenziali dell'utente dalla tabella subscription_services
        # Cerchiamo per microsoft_subscription_id_outbound
        response = supabase.table("subscription_services").select("*").eq("microsoft_subscription_id_outbound", microsoft_subscription_id_outbound).execute()
        
        if not response.data:
            raise Exception(f"Utente con microsoft_subscription_id_outbound {microsoft_subscription_id_outbound} non trovato")
        
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
            "microsoft_subscription_id_outbound": user_data.get("microsoft_subscription_id_outbound"),
            "microsoft_expiration_datetime_outbound": user_data.get("microsoft_expiration_datetime_outbound")
        }
        
    except Exception as e:
        print(f"Errore nel recupero delle credenziali outbound per subscription_id {microsoft_subscription_id_outbound}: {str(e)}")
        raise

async def get_subscription_type(subscription_id: str) -> str:
    """
    Determina se una subscription è 'inbound' o 'outbound' dal database.
    
    Args:
        subscription_id (str): ID della subscription Microsoft
        
    Returns:
        str: 'inbound' se è una subscription inbound, 'outbound' se outbound
        
    Raises:
        Exception: Se la subscription non viene trovata
    """
    try:
        supabase = get_supabase_client()
        
        # Cerca prima nelle subscription inbound
        response = supabase.table("subscription_services").select("microsoft_subscription_id_inbound").eq("microsoft_subscription_id_inbound", subscription_id).execute()
        
        if response.data:
            return "inbound"
        
        # Se non trovata, cerca nelle subscription outbound
        response = supabase.table("subscription_services").select("microsoft_subscription_id_outbound").eq("microsoft_subscription_id_outbound", subscription_id).execute()
        
        if response.data:
            return "outbound"
        
        raise Exception(f"Subscription {subscription_id} non trovata nel database")
        
    except Exception as e:
        print(f"Errore nel determinare il tipo di subscription {subscription_id}: {str(e)}")
        raise

# Mantieni anche il metodo originale per retrocompatibilità (deprecato)
async def get_user_credentials(subscription_id: str) -> Dict:
    """
    DEPRECATO: Usa get_user_credentials_inbound o get_user_credentials_outbound invece.
    """
    # Per ora cerca prima inbound, poi outbound
    try:
        return await get_user_credentials_inbound(subscription_id)
    except:
        try:
            return await get_user_credentials_outbound(subscription_id)
        except:
            raise Exception(f"Utente con subscription_id {subscription_id} non trovato in nessuna categoria")