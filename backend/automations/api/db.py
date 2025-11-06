import os
from threading import Lock
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_supabase_client: Optional[Client] = None
_client_lock = Lock()


def get_supabase_client() -> Client:
    """Return a singleton Supabase client using env SUPABASE_URL and SUPABASE_KEY."""
    global _supabase_client
    if _supabase_client is None:
        with _client_lock:
            if _supabase_client is None:
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_KEY")
                if not supabase_url or not supabase_key:
                    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
                _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client
