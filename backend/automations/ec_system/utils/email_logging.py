"""
Email Logging Utility Module

Provides centralized logging for email processing workflow.
Captures all print statements from broker and automations modules
and saves them to structured log files.
"""

import os
import sys
import io
import threading
from contextvars import ContextVar
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

# Environment variable for logs directory
LOGS_DIR = os.getenv("LOGS_DIR", "/app/logs")


def sanitize_email_for_path(email: str) -> str:
    """
    Convert email to safe directory name.
    
    Example:
        dev1@example.com -> emanuele_romano_03_at_gmail_com
    """
    if not email:
        return "unknown"
    
    # Replace @ with _at_
    sanitized = email.replace("@", "_at_")
    # Replace dots with underscores
    sanitized = sanitized.replace(".", "_")
    # Replace any other unsafe characters
    sanitized = sanitized.replace("-", "_")
    sanitized = sanitized.replace("+", "_plus_")
    
    return sanitized.lower()


def format_timestamp_for_filename(dt: Optional[datetime] = None) -> str:
    """
    Format datetime as filename-safe string.
    
    Returns:
        HH_MM_SS format string
    """
    if dt is None:
        dt = datetime.now(ZoneInfo("Europe/Rome"))
    
    return dt.strftime("%H_%M_%S")


def get_log_file_path(box_email: str, timestamp: Optional[datetime] = None, suffix: str = "") -> str:
    """
    Generate the full path for the log file.
    
    Args:
        box_email: The user's mailbox email
        timestamp: The timestamp for the log file (defaults to now)
        suffix: Suffix to add to filename (e.g., "_A" for automations, "_B" for broker)
        
    Returns:
        Full path like: /app/logs/emanuele_romano_03_at_gmail_com/14_32_45_A.txt
    """
    email_dir = sanitize_email_for_path(box_email)
    filename = format_timestamp_for_filename(timestamp) + suffix + ".txt"
    
    return os.path.join(LOGS_DIR, email_dir, filename)


class EmailLogContext:
    """
    Context manager for capturing and saving email processing logs.
    
    Thread-safe implementation that captures all print statements
    during email processing and saves them to a structured log file.
    
    Usage:
        with EmailLogContext(box_email="user@example.com") as log_ctx:
            print("This will be captured")
            log_ctx.log("This will also be captured")
    
    The log file will be automatically saved when exiting the context.
    """
    
    _active_ctx: ContextVar[Optional['EmailLogContext']] = ContextVar("email_log_context", default=None)
    _router_lock = threading.Lock()
    _stdout_router = None
    
    def __init__(self, box_email: str, timestamp: Optional[datetime] = None, service_name: str = "AUTOMATIONS"):
        """
        Initialize the log context.
        
        Args:
            box_email: The user's mailbox email (used for directory naming)
            timestamp: The timestamp for this log session (defaults to now)
            service_name: Name of the service (BROKER or AUTOMATIONS)
        """
        self.box_email = box_email
        self.timestamp = timestamp or datetime.now(ZoneInfo("Europe/Rome"))
        self.service_name = service_name
        # Add suffix based on service: _B for BROKER, _A for AUTOMATIONS
        suffix = "_A" if service_name == "AUTOMATIONS" else "_B"
        self.log_path = get_log_file_path(box_email, self.timestamp, suffix)
        self.buffer = io.StringIO()
        self._token = None
        self._started = False

    @classmethod
    def _get_console_stdout(cls):
        return getattr(sys, "__stdout__", None) or sys.stdout

    @classmethod
    def _ensure_stdout_router_installed(cls):
        with cls._router_lock:
            if cls._stdout_router is None:
                cls._stdout_router = _StdoutRouter(console=cls._get_console_stdout(), ctx_var=cls._active_ctx)
            if sys.stdout is not cls._stdout_router:
                sys.stdout = cls._stdout_router
        
    def __enter__(self):
        """Start capturing output."""
        self._started = True
        EmailLogContext._ensure_stdout_router_installed()
        self._token = EmailLogContext._active_ctx.set(self)
        
        # Log session start
        self.log(f"\n{'='*80}")
        self.log(f"📧 [{self.service_name}] EMAIL PROCESSING LOG SESSION STARTED")
        self.log(f"📬 Mailbox: {self.box_email}")
        self.log(f"🕐 Timestamp: {self.timestamp.isoformat()}")
        self.log(f"{'='*80}\n")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop capturing and save the log file."""
        # Log session end
        if exc_type:
            self.log(f"\n{'='*80}")
            self.log(f"❌ [{self.service_name}] SESSION ENDED WITH ERROR: {exc_type.__name__}: {exc_val}")
            self.log(f"{'='*80}\n")
        else:
            self.log(f"\n{'='*80}")
            self.log(f"✅ [{self.service_name}] EMAIL PROCESSING LOG SESSION COMPLETED")
            self.log(f"{'='*80}\n")
        
        if self._token is not None:
            EmailLogContext._active_ctx.reset(self._token)
            self._token = None
        
        # Save the log file
        self._save_log()
        
        # Close buffer
        self.buffer.close()
        
        return False  # Don't suppress exceptions
    
    def log(self, message: str):
        """
        Explicitly log a message with timestamp.
        
        Args:
            message: The message to log
        """
        timestamp = datetime.now(ZoneInfo("Europe/Rome")).strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        print(formatted)
    
    def _save_log(self):
        """Save the captured logs to the file system."""
        try:
            # Ensure directory exists
            log_dir = os.path.dirname(self.log_path)
            os.makedirs(log_dir, exist_ok=True)
            
            # Write the log content (append mode to allow both broker and automations to write)
            log_content = self.buffer.getvalue()
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(log_content)
            
            # Print to original stdout (for container logs)
            EmailLogContext._get_console_stdout().write(f"\n💾 [EMAIL_LOGGING] Log saved to: {self.log_path}\n")
                
        except Exception as e:
            # Print error to original stdout
            EmailLogContext._get_console_stdout().write(f"\n❌ [EMAIL_LOGGING] Failed to save log: {e}\n")
    
    @classmethod
    def get_current(cls) -> Optional['EmailLogContext']:
        """
        Get the current active log context for this thread.
        
        Returns:
            The current EmailLogContext or None if not in a logging context
        """
        return cls._active_ctx.get()
    
    def get_log_content(self) -> str:
        """
        Get the current log content as a string.
        
        Returns:
            The accumulated log content
        """
        return self.buffer.getvalue()


class _StdoutRouter:
    """A single global sys.stdout proxy that routes writes to the active EmailLogContext (per-task via ContextVar)."""

    def __init__(self, console, ctx_var: ContextVar):
        self._console = console
        self._ctx_var = ctx_var

    def write(self, message: str):
        ctx = self._ctx_var.get()
        if ctx is not None and getattr(ctx, "buffer", None) is not None and not ctx.buffer.closed:
            try:
                ctx.buffer.write(message)
            except Exception:
                pass
        return self._console.write(message)

    def flush(self):
        try:
            self._console.flush()
        except Exception:
            pass

    def fileno(self):
        return self._console.fileno()

    def isatty(self):
        return getattr(self._console, "isatty", lambda: False)()

    @property
    def encoding(self):
        return getattr(self._console, "encoding", "utf-8")



# Convenience function for global access
def log_message(message: str):
    """
    Log a message to the current context if one exists.
    Falls back to regular print if no context is active.
    
    Args:
        message: The message to log
    """
    ctx = EmailLogContext.get_current()
    if ctx:
        ctx.log(message)
    else:
        print(message)
