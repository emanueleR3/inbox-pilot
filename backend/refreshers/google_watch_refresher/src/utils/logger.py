from datetime import datetime


class Logger:

    @staticmethod
    def log_info(msg):
        print(f"[{datetime.utcnow().isoformat()}] INFO: {msg}")

    @staticmethod
    def log_error(msg):
        print(f"[{datetime.utcnow().isoformat()}] ERROR: {msg}")
