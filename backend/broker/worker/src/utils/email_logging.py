"""
Email Logging Utility Module for Broker

Provides centralized logging for email processing workflow.
Captures all print statements from broker modules
and saves them to structured log files.
"""

import os
import sys
import io
import threading
from datetime import datetime, timezone
from contextlib import redirect_stdout
from typing import Optional

# Try to import ZoneInfo (Python 3.9+)
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

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
        Full path like: /app/logs/emanuele_romano_03_at_gmail_com/14_32_45_B.txt
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
    
    # Thread-local storage for nested contexts
    _local = threading.local()
    
    def __init__(self, box_email: str, timestamp: Optional[datetime] = None, service_name: str = "BROKER"):
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
        self._old_stdout = None
        self._started = False
        
    def __enter__(self):
        """Start capturing output."""
        self._started = True
        self._old_stdout = sys.stdout
        
        # Create a custom stdout that writes to both console and buffer
        self._dual_writer = DualWriter(self._old_stdout, self.buffer)
        sys.stdout = self._dual_writer
        
        # Store context in thread-local storage for access from other modules
        if not hasattr(EmailLogContext._local, 'stack'):
            EmailLogContext._local.stack = []
        EmailLogContext._local.stack.append(self)
        
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
        
        # Restore stdout
        sys.stdout = self._old_stdout
        
        # Remove from thread-local stack
        if hasattr(EmailLogContext._local, 'stack') and EmailLogContext._local.stack:
            EmailLogContext._local.stack.pop()
        
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
            if self._old_stdout:
                self._old_stdout.write(f"\n💾 [EMAIL_LOGGING] Log saved to: {self.log_path}\n")
                
        except Exception as e:
            # Print error to original stdout
            if self._old_stdout:
                self._old_stdout.write(f"\n❌ [EMAIL_LOGGING] Failed to save log: {e}\n")
    
    @classmethod
    def get_current(cls) -> Optional['EmailLogContext']:
        """
        Get the current active log context for this thread.
        
        Returns:
            The current EmailLogContext or None if not in a logging context
        """
        if hasattr(cls._local, 'stack') and cls._local.stack:
            return cls._local.stack[-1]
        return None
    
    def get_log_content(self) -> str:
        """
        Get the current log content as a string.
        
        Returns:
            The accumulated log content
        """
        return self.buffer.getvalue()


class DualWriter:
    """
    A file-like object that writes to two destinations simultaneously.
    Used to capture output while also displaying it in the console.
    """
    
    def __init__(self, original_stdout, buffer: io.StringIO):
        self.original_stdout = original_stdout
        self.buffer = buffer
    
    def write(self, message: str):
        """Write to both destinations."""
        self.original_stdout.write(message)
        self.buffer.write(message)
    
    def flush(self):
        """Flush both destinations."""
        self.original_stdout.flush()
        self.buffer.flush()
    
    def fileno(self):
        """Return original stdout's file descriptor."""
        return self.original_stdout.fileno()


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
