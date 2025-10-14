from datetime import datetime
import traceback

def log_info(msg: str):
    """
    Log di livello INFO con timestamp UTC
    """
    print(f"[{datetime.utcnow().isoformat()}] INFO: {msg}")

def log_error(msg: str, exc: Exception | None = None):
    """
    Log di livello ERROR con timestamp UTC
    """
    print(f"[{datetime.utcnow().isoformat()}] ERROR: {msg}")
    if exc:
        traceback.print_exception(type(exc), exc, exc.__traceback__)