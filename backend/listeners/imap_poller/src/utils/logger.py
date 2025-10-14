from datetime import datetime

def log_info(msg):
    print(f"[{datetime.utcnow().isoformat()}] INFO: {msg}")

def log_error(msg):
    print(f"[{datetime.utcnow().isoformat()}] ERROR: {msg}")