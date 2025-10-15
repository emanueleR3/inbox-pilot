from supabase import create_client, Client
from src.core.config import settings
from threading import Lock

_supabase_client: Client | None = None
_client_lock = Lock()

def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        with _client_lock:
            if _supabase_client is None:  # double-checked locking
                _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client