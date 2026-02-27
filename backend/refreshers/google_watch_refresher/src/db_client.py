import os
from supabase import create_client, Client
from threading import Lock
from typing import List
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64
import hashlib
from src.utils.logger import Logger

load_dotenv()

_supabase_client: Client | None = None
_client_lock = Lock()

_cipher = None
_cipher_lock = Lock()


def _get_cipher():
    global _cipher
    if _cipher is None:
        with _cipher_lock:
            if _cipher is None:
                encryption_key_str = os.getenv("ENCRYPTION_KEY_TOKEN")
                if not encryption_key_str:
                    raise ValueError("ENCRYPTION_KEY_TOKEN non trovata nelle variabili d'ambiente")
                encryption_key = encryption_key_str.encode()
                key_hash = hashlib.sha256(encryption_key).digest()
                fernet_key = base64.urlsafe_b64encode(key_hash)
                _cipher = Fernet(fernet_key)
    return _cipher


def _decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        return ""
    cipher = _get_cipher()
    return cipher.decrypt(encrypted_token.encode()).decode()


def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        with _client_lock:
            if _supabase_client is None:
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_KEY")
                if not supabase_url or not supabase_key:
                    raise ValueError(
                        "SUPABASE_URL e SUPABASE_KEY devono essere configurati nelle variabili d'ambiente"
                    )
                _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client


def get_all_active_users() -> list[str]:
    """
    Restituisce la lista delle email di tutti gli utenti Google attivi.

    Un utente è considerato attivo se:
    - Ha un hashed_access_token non nullo (ha completato l'autenticazione OAuth)
    - Usa "google" come email_provider
    """
    try:
        supabase = get_supabase_client()
        response = (
            supabase.table("subscription_services")
            .select("email")
            .not_.is_("hashed_access_token", "null")
            .eq("email_provider", "google")
            .execute()
        )

        if not response.data:
            Logger.log_info("### GOOGLE WATCH 📭 Nessun utente Google attivo trovato.")
            return []

        emails = [record["email"] for record in response.data if record.get("email")]
        Logger.log_info(f"### GOOGLE WATCH 📋 Trovati {len(emails)} utenti Google attivi.")
        return emails

    except Exception as e:
        Logger.log_error(f"### GOOGLE WATCH ❌ Errore nel recupero degli utenti attivi: {str(e)}")
        return []


def get_user_credentials(email: str) -> dict:
    """
    Recupera le credenziali OAuth decriptate per un utente specifico.
    """
    try:
        supabase = get_supabase_client()
        response = (
            supabase.table("subscription_services")
            .select("email, hashed_access_token, hashed_refresh_token")
            .eq("email", email.lower())
            .execute()
        )

        if not response.data:
            raise Exception(f"Utente con email {email} non trovato")

        user_data = response.data[0]

        access_token = ""
        refresh_token = ""
        if user_data.get("hashed_access_token"):
            access_token = _decrypt_token(user_data["hashed_access_token"])
        if user_data.get("hashed_refresh_token"):
            refresh_token = _decrypt_token(user_data["hashed_refresh_token"])

        return {
            "email": user_data.get("email"),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    except Exception as e:
        Logger.log_error(f"### GOOGLE WATCH ❌ Errore nel recupero credenziali per {email}: {str(e)}")
        raise
