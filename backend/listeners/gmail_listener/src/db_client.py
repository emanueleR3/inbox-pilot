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

def get_user_credentials(email: str) -> Dict:
    """
    Recupera le credenziali dell'utente dal database Supabase.
    I token vengono automaticamente decrittati.
    
    Args:
        email (str): Email dell'utente
        
    Returns:
        dict: Dizionario contenente le credenziali dell'utente decrittate
        
    Raises:
        Exception: Se l'utente non viene trovato o si verifica un errore
    """
    try:
        supabase = get_supabase_client()
        
        # Query per ottenere le credenziali dell'utente dalla tabella subscription_services
        response = supabase.table("subscription_services").select("*").eq("email", email.lower()).execute()
        
        if not response.data:
            raise Exception(f"Utente con email {email} non trovato")
        
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
            "oauth_user_id": user_data.get("oauth_user_id"),
            "microsoft_subscription_id": user_data.get("microsoft_subscription_id"),
            "microsoft_expiration_datetime": user_data.get("microsoft_expiration_datetime")
        }
        
    except Exception as e:
        print(f"Errore nel recupero delle credenziali per {email}: {str(e)}")
        raise

def update_history_id(email: str, history_id: str) -> bool:
    """
    Aggiorna l'history_id di Gmail per un utente specifico.
    
    Args:
        email (str): Email dell'utente
        history_id (str): Nuovo history_id da salvare
        
    Returns:
        bool: True se l'aggiornamento è avvenuto con successo, False altrimenti
    """
    try:
        supabase = get_supabase_client()
        
        # Aggiorna l'history_id nella tabella users
        response = supabase.table("subscription_services").update({
            "history_id": history_id
        }).eq("email", email.lower()).execute()
        
        if not response.data:
            print(f"Nessun utente trovato con email {email} per aggiornare history_id")
            return False
            
        print(f"History ID aggiornato con successo per {email}: {history_id}")
        return True
        
    except Exception as e:
        print(f"Errore nell'aggiornamento dell'history_id per {email}: {str(e)}")
        return False