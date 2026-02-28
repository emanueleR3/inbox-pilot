from langchain.tools import tool
from typing import Optional, List, Dict, Any
from automations.chatbot.services import email_service
from automations.chatbot.db.db import get_supabase_client, get_colleagues_by_subscription, get_user_calendar_info
from automations.chatbot.services.calendar_service import (
    find_common_free_slots,
    check_slot_availability,
    schedule_calendar_event
)
from automations.ec_system.utils.utils import decrypt
import os
import httpx
import base64
import hashlib
from cryptography.fernet import Fernet
from datetime import datetime, timedelta, timezone
from threading import Lock


# Token refresh configuration
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
TOKEN_REFRESH_THRESHOLD_SECONDS = 300  # Refresh if token expires within 5 minutes

# Cipher for token encryption (singleton pattern)
_cipher = None
_cipher_lock = Lock()


def _get_cipher():
    """Get the Fernet cipher for token encryption/decryption."""
    global _cipher
    if _cipher is None:
        with _cipher_lock:
            if _cipher is None:
                encryption_key_str = os.getenv("ENCRYPTION_KEY_TOKEN")
                if not encryption_key_str:
                    raise ValueError("ENCRYPTION_KEY_TOKEN not found in environment variables")
                
                encryption_key = encryption_key_str.encode()
                key_hash = hashlib.sha256(encryption_key).digest()
                fernet_key = base64.urlsafe_b64encode(key_hash)
                _cipher = Fernet(fernet_key)
    return _cipher


def _decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted token."""
    if not encrypted_token:
        return ""
    return decrypt(encrypted_token, "token")


def _encrypt_token(token: str) -> str:
    """Encrypt a token for storage using Fernet (AES-256)."""
    if not token:
        return ""
    cipher = _get_cipher()
    return cipher.encrypt(token.encode()).decode()


def _refresh_microsoft_token_sync(refresh_token: str) -> dict:
    """
    Synchronously refresh Microsoft access token using refresh token.
    
    Args:
        refresh_token: The refresh token to use
        
    Returns:
        dict with access_token, refresh_token (if rotated), and expires_in
    """
    client_id = os.getenv("MICROSOFT_APPLICATION_ID_CLIENT")
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET_VALUE")
    
    if not client_id or not client_secret:
        raise ValueError("Microsoft OAuth credentials not configured")
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(MICROSOFT_TOKEN_URL, data=data)
        if resp.status_code != 200:
            raise Exception(f"Microsoft token refresh failed: {resp.text}")
        return resp.json()


def _refresh_google_token_sync(refresh_token: str) -> dict:
    """
    Synchronously refresh Google access token using refresh token.
    
    Args:
        refresh_token: The refresh token to use
        
    Returns:
        dict with access_token and expires_in
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials not configured")
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(GOOGLE_TOKEN_URL, data=data)
        if resp.status_code != 200:
            raise Exception(f"Google token refresh failed: {resp.text}")
        return resp.json()


def _update_tokens_in_db(email: str, access_token: str, expires_in: int, refresh_token: str = None) -> bool:
    """
    Update tokens in the database after a refresh.
    
    Args:
        email: User email
        access_token: New access token
        expires_in: Token validity in seconds
        refresh_token: New refresh token (if provider rotated it)
        
    Returns:
        bool: True if update successful
    """
    try:
        supabase = get_supabase_client()
        
        # Calculate new expiry time
        new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        new_expiry_iso = new_expiry.isoformat()
        
        # Encrypt tokens
        encrypted_access_token = _encrypt_token(access_token)
        
        update_data = {
            "hashed_access_token": encrypted_access_token,
            "expiry_token": new_expiry_iso
        }
        
        # Update refresh token if provided (Microsoft may rotate it)
        if refresh_token:
            encrypted_refresh_token = _encrypt_token(refresh_token)
            update_data["hashed_refresh_token"] = encrypted_refresh_token
        
        response = supabase.table("subscription_services").update(update_data).eq("email", email.lower()).execute()
        
        if response.data:
            print(f"✅ [TOKEN REFRESH] Tokens updated for {email}, expires at {new_expiry_iso}")
            return True
        else:
            print(f"❌ [TOKEN REFRESH] Failed to update tokens for {email}")
            return False
            
    except Exception as e:
        print(f"❌ [TOKEN REFRESH] Error updating tokens for {email}: {str(e)}")
        return False


def _get_access_token_for_email(email: str) -> Optional[str]:
    """Retrieve and decrypt access token for a given email address. Refreshes if expired."""
    try:
        supabase = get_supabase_client()
        response = supabase.table("subscription_services").select(
            "hashed_access_token, hashed_refresh_token, expiry_token, email_provider"
        ).eq("email", email.lower()).execute()
        
        if not response.data:
            print(f"No credentials found for email {email}")
            return None
        
        user_data = response.data[0]
        provider = user_data.get("email_provider", "").lower()
        
        # Check if token is expired or expiring soon (within 5 minutes)
        expiry_token = user_data.get("expiry_token")
        needs_refresh = False
        
        if expiry_token:
            try:
                expiry_time = datetime.fromisoformat(expiry_token.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                time_until_expiry = expiry_time - now
                
                # If token expires in less than 5 minutes, it needs refresh
                if time_until_expiry.total_seconds() < TOKEN_REFRESH_THRESHOLD_SECONDS:
                    needs_refresh = True
                    print(f"🔄 [TOKEN REFRESH] Token for {email} expires in {int(time_until_expiry.total_seconds())} seconds, refreshing...")
            except Exception as e:
                print(f"Error checking token expiry: {str(e)}")
        
        # Attempt token refresh if needed
        if needs_refresh and user_data.get("hashed_refresh_token"):
            refresh_token = _decrypt_token(user_data["hashed_refresh_token"])
            
            if refresh_token:
                try:
                    if provider == "microsoft":
                        refreshed = _refresh_microsoft_token_sync(refresh_token)
                    elif provider == "google":
                        refreshed = _refresh_google_token_sync(refresh_token)
                    else:
                        print(f"⚠️ [TOKEN REFRESH] Unknown provider '{provider}' for {email}, cannot refresh")
                        # Return current token even if expiring
                        if user_data.get("hashed_access_token"):
                            return _decrypt_token(user_data["hashed_access_token"])
                        return None
                    
                    # Extract new tokens
                    new_access_token = refreshed.get("access_token")
                    expires_in = refreshed.get("expires_in", 3600)
                    new_refresh_token = refreshed.get("refresh_token")  # Microsoft may rotate
                    
                    if new_access_token:
                        # Update tokens in database
                        _update_tokens_in_db(email, new_access_token, expires_in, new_refresh_token)
                        print(f"✅ [TOKEN REFRESH] Successfully refreshed token for {email} ({provider})")
                        return new_access_token
                    else:
                        print(f"❌ [TOKEN REFRESH] No access token in refresh response for {email}")
                        
                except Exception as refresh_error:
                    print(f"❌ [TOKEN REFRESH] Failed to refresh token for {email}: {str(refresh_error)}")
                    # Fall back to current token
        
        # Return current access token (either refresh not needed or refresh failed)
        if user_data.get("hashed_access_token"):
            return _decrypt_token(user_data["hashed_access_token"])
        
        return None
    except Exception as e:
        print(f"Error retrieving access token for {email}: {str(e)}")
        return None


def _decrypt_password(encrypted_password: str) -> str:
    """Decrypt an encrypted password using the shared decrypt utility."""
    if not encrypted_password:
        return ""
    try:
        decrypted = decrypt(encrypted_password, "pass")
        return decrypted
    except Exception as e:
        import traceback
        print(f"Decryption failed: {type(e).__name__}: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise


def _get_imap_smtp_credentials(email: str) -> Optional[dict]:
    """
    Retrieve IMAP/SMTP credentials for a given email address.
    
    Returns a dictionary with:
        - host: SMTP server for sending, IMAP server for receiving
        - smtp_host: SMTP server hostname
        - smtp_port: SMTP server port
        - imap_host: IMAP server hostname
        - imap_port: IMAP server port
        - password: Decrypted password
        - email: Email address
    
    Returns None if no IMAP/SMTP configuration is found.
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("subscription_services").select(
            "email, imap_server, imap_port, smtp_server, smtp_port, hashed_password"
        ).eq("email", email.lower()).execute()
        
        if not response.data:
            print(f"No IMAP/SMTP credentials found for email {email}")
            return None
        
        user_data = response.data[0]
        print(f"Found user data for {email}: imap_server={user_data.get('imap_server')}, smtp_server={user_data.get('smtp_server')}, has_password={bool(user_data.get('hashed_password'))}")
        
        # Check if IMAP/SMTP is configured
        if not user_data.get("imap_server") or not user_data.get("smtp_server"):
            print(f"IMAP/SMTP not configured for email {email}")
            return None
        
        # Decrypt the password
        decrypted_password = ""
        if user_data.get("hashed_password"):
            try:
                decrypted_password = _decrypt_password(user_data["hashed_password"])
            except Exception as decrypt_error:
                print(f"Error decrypting password for {email}: {str(decrypt_error)}")
                return None
        
        if not decrypted_password:
            print(f"No password found for IMAP/SMTP email {email}")
            return None
        
        return {
            "email": user_data.get("email"),
            "smtp_host": user_data.get("smtp_server"),
            "smtp_port": user_data.get("smtp_port", 587),
            "imap_host": user_data.get("imap_server"),
            "imap_port": user_data.get("imap_port", 993),
            "password": decrypted_password
        }
    except Exception as e:
        import traceback
        print(f"Error retrieving IMAP/SMTP credentials for {email}: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return None

@tool(
        name_or_callable="send_email",
        description="Send an email using Google OAuth, Microsoft OAuth, IMAP/SMTP, or plain SMTP. "
                    "Use 'google' provider if the email is a Google account. "
                    "For 'imap' or 'smtp' provider, credentials will be automatically retrieved from the system. ",
        args_schema=(
            {
                "type": "object",
                "properties": {
                    "sender_address": {
                        "type": "string",
                        "description": "Email address of the sender"
                    },
                    "receiver_address": {
                        "type": "string",
                        "description": "Email address of the recipient"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body content"
                    },
                    "provider": {
                        "type": "string",
                        "description": "'google' (default), 'microsoft', 'imap', or 'smtp'. Use 'imap' for configured IMAP/SMTP accounts. Use 'smtp' only with manual host/password credentials.",
                        "default": "google"
                    },
                    "password": {
                        "type": ["string", "null"],
                        "description": "Password or app password (REQUIRED for 'smtp', auto-retrieved for 'imap')"
                    },
                    "host": {
                        "type": ["string", "null"],
                        "description": "SMTP host like 'smtp.gmail.com' (REQUIRED for 'smtp', auto-retrieved for 'imap')"
                    },
                    "body_type": {
                        "type": "string",
                        "description": "'text' or 'html' (default: 'text')",
                        "default": "text"
                    },
                    "cc_recipients": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                        "description": "List of CC email addresses"
                    },
                    "bcc_recipients": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                        "description": "List of BCC email addresses"
                    },
                    "attachments": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                        "description": "List of file paths to attach"
                    },
                    "access_token": {
                        "type": ["string", "null"],
                        "description": "OAuth access token (automatically retrieved for google/microsoft)"
                    },
                    "port": {
                        "type": ["integer", "null"],
                        "description": "SMTP port like 587 or 465 (optional, defaults to 587)"
                    }
                },
                "required": ["sender_address", "receiver_address", "subject", "body"]
            }
        )
)
def send_email(
    sender_address: str,
    receiver_address: str,
    subject: str,
    body: str,
    provider: str = "google",
    password: Optional[str] = None,
    host: Optional[str] = None,
    body_type: str = "text",
    cc_recipients: Optional[List[str]] = None,
    bcc_recipients: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
    access_token: Optional[str] = None,
    port: Optional[int] = None
) -> str:
    
    # Auto-fetch access token for Google/Microsoft if not provided
    if provider in ['google', 'microsoft'] and not access_token:
        print(f"Fetching access token for {sender_address}...")
        access_token = _get_access_token_for_email(sender_address)
        if not access_token:
            return f"Error: Could not retrieve access token for {sender_address}. Please ensure the email is configured in the system."
    
    # Auto-fetch IMAP/SMTP credentials if provider is 'imap' or 'smtp'
    if provider == 'imap' or provider == 'smtp':
        print(f"Fetching IMAP/SMTP credentials for {sender_address}...")
        credentials = _get_imap_smtp_credentials(sender_address)
        if not credentials:
            return f"Error: Could not retrieve IMAP/SMTP credentials for {sender_address}. Please ensure the email is configured with IMAP/SMTP settings."
        
        # Use the retrieved credentials
        host = credentials["smtp_host"]
        port = credentials["smtp_port"]
        password = credentials["password"]
        # Switch to 'smtp' provider for the actual sending since we now have the credentials
        provider = "smtp"

    return email_service.send_email(
        sender_address=sender_address,
        password=password or "",
        receiver_address=receiver_address,
        subject=subject,
        body=body,
        provider=provider,
        host=host,
        body_type=body_type,
        cc_recipients=cc_recipients,
        bcc_recipients=bcc_recipients,
        attachments=attachments,
        access_token=access_token,
        port=port
    )
    
@tool(
    name_or_callable="create_draft_email",
    description="""Create an email draft in the user's mailbox without sending it. Use this when the user wants to prepare an email for later review or editing before sending.

Supported providers: 'google' (Gmail) and 'microsoft' (Outlook/Microsoft 365).
Access tokens are automatically retrieved from the system - you don't need to provide them.

When to use this tool:
- User wants to draft an email for later review
- User wants to prepare a response but not send immediately
- User asks to "save" or "draft" an email

Returns: A confirmation message with the draft ID if successful, or an error message if failed.""",
    args_schema=(
        {
            "type": "object",
            "properties": {
                "sender_address": {
                    "type": "string",
                    "description": "The email address of the sender. Must be a configured email in the system (e.g., 'user@gmail.com' or 'user@outlook.com')"
                },
                "receiver_address": {
                    "type": "string",
                    "description": "The primary recipient's email address (e.g., 'recipient@example.com')"
                },
                "subject": {
                    "type": "string",
                    "description": "The email subject line. Should be clear and descriptive."
                },
                "body": {
                    "type": "string",
                    "description": "The main content of the email. Can be plain text or HTML based on body_type parameter."
                },
                "provider": {
                    "type": "string",
                    "description": "Email provider: 'google' for Gmail accounts, 'microsoft' for Outlook/Microsoft 365. Default: 'google'",
                    "default": "google"
                },
                "access_token": {
                    "type": ["string", "null"],
                    "description": "OAuth access token. Leave empty - automatically retrieved from system based on sender_address."
                },
                "body_type": {
                    "type": "string",
                    "description": "Content type: 'text' for plain text, 'html' for HTML formatted emails. Default: 'text'",
                    "default": "text"
                },
                "cc_recipients": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "description": "List of CC (carbon copy) recipient email addresses. Optional."
                },
                "bcc_recipients": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "description": "List of BCC (blind carbon copy) recipient email addresses. Optional."
                },
                "attachments": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "description": "List of file paths to attach to the draft. Optional."
                }
            },
            "required": ["sender_address", "receiver_address", "subject", "body"]
        }
    )
)
def create_draft_email(
    sender_address: str,
    receiver_address: str,
    subject: str,
    body: str,
    provider: str = "google",
    access_token: Optional[str] = None,
    body_type: str = "text",
    cc_recipients: Optional[List[str]] = None,
    bcc_recipients: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None
) -> str:
    if provider in ['google', 'microsoft'] and not access_token:
        print(f"Fetching access token for {sender_address} to create draft...")
        access_token = _get_access_token_for_email(sender_address)
        if not access_token:
            return f"Error: Could not retrieve access token for {sender_address}. Please ensure the email is configured in the system."

    return email_service.create_draft(
        sender_address=sender_address,
        receiver_address=receiver_address,
        subject=subject,
        body=body,
        provider=provider,
        access_token=access_token,
        body_type=body_type,
        cc_recipients=cc_recipients,
        bcc_recipients=bcc_recipients,
        attachments=attachments
    )


@tool(
    name_or_callable="retrieve_last_n_emails",
    description="""Retrieve the most recent N emails from a user's mailbox. Use this to get an overview of recent email activity, find recent conversations, or gather context about the user's inbox.

Supported providers: 'google' (Gmail), 'microsoft' (Outlook/Microsoft 365), and 'imap' (generic IMAP servers).
All credentials are automatically retrieved from the system - you don't need to provide them.

When to use this tool:
- User asks "what are my recent emails?"
- User wants to check their inbox
- You need context about recent email conversations
- User asks to summarize recent emails

IMPORTANT: The results include message IDs and thread IDs that can be used with other tools like get_thread_messages, reply_to_email, forward_email, or delete_emails.

Returns: A formatted string containing email details (sender, subject, date, snippet, message_id, thread_id) for each retrieved email.""",
    args_schema=(
        {
            "type": "object",
            "properties": {
                "email_address": {
                    "type": "string",
                    "description": "The email address to retrieve emails from. Must be configured in the system."
                },
                "n": {
                    "type": "integer",
                    "description": "Number of recent emails to retrieve. Default: 10, Maximum: 20. Use smaller values for quick overviews.",
                    "default": 10
                },
                "provider": {
                    "type": "string",
                    "description": "Email provider: 'google' for Gmail, 'microsoft' for Outlook/M365, 'imap' for other providers. Default: 'google'",
                    "default": "google"
                },
                "access_token": {
                    "type": ["string", "null"],
                    "description": "OAuth access token. Leave empty - automatically retrieved for google/microsoft providers."
                },
                "host": {
                    "type": ["string", "null"],
                    "description": "IMAP server hostname. Leave empty - automatically retrieved for 'imap' provider."
                },
                "password": {
                    "type": ["string", "null"],
                    "description": "Email password. Leave empty - automatically retrieved for 'imap' provider."
                },
                "port": {
                    "type": ["integer", "null"],
                    "description": "IMAP port number. Default: 993 (SSL). Only used for 'imap' provider.",
                    "default": 993
                }
            },
            "required": ["email_address"]
        }
    )
)
def retrieve_last_n_emails(
    email_address: str,
    n: int = 10,
    provider: str = "google",
    access_token: Optional[str] = None,
    host: Optional[str] = None,
    password: Optional[str] = None,
    port: Optional[int] = 993
) -> str:
    # Auto-fetch access token for Google/Microsoft if not provided
    if provider in ['google', 'microsoft'] and not access_token:
        print(f"Fetching access token for {email_address} to retrieve emails...")
        access_token = _get_access_token_for_email(email_address)
        if not access_token:
            return f"Error: Could not retrieve access token for {email_address}. Please ensure the email is configured in the system."
    
    # Auto-fetch IMAP credentials if provider is 'imap' and credentials not provided
    if provider == 'imap' and (not host or not password):
        print(f"Fetching IMAP credentials for {email_address}...")
        credentials = _get_imap_smtp_credentials(email_address)
        if not credentials:
            return f"Error: Could not retrieve IMAP credentials for {email_address}. Please ensure the email is configured with IMAP/SMTP settings."
        
        host = credentials["imap_host"]
        port = credentials["imap_port"]
        password = credentials["password"]

    return email_service.retrieve_last_n_emails(
        n=n,
        provider=provider,
        access_token=access_token,
        host=host,
        username=email_address,
        password=password,
        port=port
    )

# TODO Fargli capire che non deve mettere dati a caso perché senno sicuro non trova nulla.
# Si potrebbe anche fare che se non trova nulla, riprova con una ricerca meno stringente.
# Per ora mi ha scazzato la email (ho detto email da Loris Catalano e ha cercato con sender=loris.catalano@example.com)
@tool(
    name_or_callable="search_emails",
    description="""Search for emails matching specified criteria. Use this to find specific emails by sender, subject, keywords, date range, or raw search queries.

Supported providers: 'google' (Gmail), 'microsoft' (Outlook/Microsoft 365), and 'imap' (generic IMAP servers).
All credentials are automatically retrieved from the system - you don't need to provide them.

When to use this tool:
- User wants to find emails from a specific person
- User wants to find emails about a specific topic
- User wants to find emails within a date range
- User asks "find emails about...", "search for emails from...", etc.

IMPORTANT: The results include message IDs and thread IDs that can be used with other tools like get_thread_messages, reply_to_email, forward_email, or delete_emails.

Returns: A formatted string containing matching emails with details (sender, subject, date, snippet, message_id, thread_id).""",
    args_schema=(
        {
            "type": "object",
            "properties": {
                "email_address": {
                    "type": "string",
                    "description": "The email address to search in. Must be configured in the system."
                },
                "query": {
                    "type": ["string", "null"],
                    "description": "Raw search query. For Gmail: use format like 'from:user@example.com is:unread'. For general search, just use keywords."
                },
                "sender": {
                    "type": ["string", "null"],
                    "description": "Filter by sender email address (e.g., 'boss@company.com'). Finds all emails from this sender. Fill this field only if you are sure of the email address."
                },
                "subject": {
                    "type": ["string", "null"],
                    "description": "Filter by subject line keywords (e.g., 'meeting notes'). Matches partial subject text."
                },
                "keywords": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "description": "List of keywords to search for in email body/subject (e.g., ['invoice', 'payment'])."
                },
                "after_date": {
                    "type": ["string", "null"],
                    "description": "Only return emails after this date. Format: 'YYYY/MM/DD' or 'YYYY-MM-DD' (e.g., '2024/01/01')."
                },
                "before_date": {
                    "type": ["string", "null"],
                    "description": "Only return emails before this date. Format: 'YYYY/MM/DD' or 'YYYY-MM-DD' (e.g., '2024/12/31')."
                },
                "provider": {
                    "type": "string",
                    "description": "Email provider: Use 'google' for Gmail, 'microsoft' for Outlook/M365, 'imap' for other providers. Default: 'google'",
                    "default": "google"
                },
                "access_token": {
                    "type": ["string", "null"],
                    "description": "OAuth access token. Leave empty - automatically retrieved for google/microsoft providers."
                },
                "label_ids": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "description": "Gmail only: List of label IDs to filter by (e.g., ['INBOX', 'IMPORTANT', 'STARRED'])."
                },
                "include_spam_trash": {
                    "type": "boolean",
                    "description": "Include spam and trash folders in search results. Default: false",
                    "default": False
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Default: 10, Maximum: 50.",
                    "default": 10
                },
                "host": {
                    "type": ["string", "null"],
                    "description": "IMAP server hostname. Leave empty - automatically retrieved for 'imap' provider."
                },
                "password": {
                    "type": ["string", "null"],
                    "description": "Email password. Leave empty - automatically retrieved for 'imap' provider."
                },
                "port": {
                    "type": ["integer", "null"],
                    "description": "IMAP port number. Default: 993 (SSL). Only used for 'imap' provider.",
                    "default": 993
                }
            },
            "required": ["email_address"]
        }
    )
)
def search_emails(
    email_address: str,
    query: Optional[str] = None,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    after_date: Optional[str] = None,
    before_date: Optional[str] = None,
    provider: str = "google",
    access_token: Optional[str] = None,
    label_ids: Optional[List[str]] = None,
    include_spam_trash: bool = False,
    max_results: int = 10,
    host: Optional[str] = None,
    password: Optional[str] = None,
    port: Optional[int] = 993
) -> str:
    # Auto-fetch access token for Google/Microsoft if not provided
    if provider in ['google', 'microsoft'] and not access_token:
        print(f"Fetching access token for {email_address} to search emails...")
        access_token = _get_access_token_for_email(email_address)
        if not access_token:
            return f"Error: Could not retrieve access token for {email_address}. Please ensure the email is configured in the system."
    
    # Auto-fetch IMAP credentials if provider is 'imap' and credentials not provided
    if provider == 'imap' and (not host or not password):
        print(f"Fetching IMAP credentials for {email_address}...")
        credentials = _get_imap_smtp_credentials(email_address)
        if not credentials:
            return f"Error: Could not retrieve IMAP credentials for {email_address}. Please ensure the email is configured with IMAP/SMTP settings."
        
        host = credentials["imap_host"]
        port = credentials["imap_port"]
        password = credentials["password"]

    return email_service.search_emails(
        provider=provider,
        access_token=access_token,
        query=query,
        sender=sender,
        subject=subject,
        keywords=keywords,
        after_date=after_date,
        before_date=before_date,
        label_ids=label_ids,
        include_spam_trash=include_spam_trash,
        max_results=max_results,
        host=host,
        username=email_address,
        password=password,
        port=port
    )


@tool(
    name_or_callable="get_thread_messages",
    description="""Retrieve all messages in an email thread/conversation. Use this to get the full context of an email conversation, see the complete history of an exchange, or understand the discussion before replying.

Supported providers: 'google' (Gmail) and 'microsoft' (Outlook/Microsoft 365).
All credentials are automatically retrieved from the system.

When to use this tool:
- User wants to see the full email conversation
- You need context before replying to an email
- User asks to "show the thread" or "show the conversation"

IMPORTANT: You MUST first use search_emails or retrieve_last_n_emails to get a valid thread_id. Do NOT make up or guess thread IDs - they must come from actual email data.

Returns: A formatted string containing all messages in the thread in chronological order.""",
    args_schema=(
        {
            "type": "object",
            "properties": {
                "email_address": {
                    "type": "string",
                    "description": "The email address to retrieve the thread from. Must be configured in the system."
                },
                "thread_id": {
                    "type": "string",
                    "description": "The thread/conversation ID. MUST be obtained from search_emails or retrieve_last_n_emails results. For Gmail: hexadecimal string like '18abc123def456gh'. For Microsoft: use the conversationId field."
                },
                "provider": {
                    "type": "string",
                    "description": "Email provider: 'google' for Gmail, 'microsoft' for Outlook/M365. Default: 'google'",
                    "default": "google"
                },
                "access_token": {
                    "type": ["string", "null"],
                    "description": "OAuth access token. Leave empty - automatically retrieved."
                },
                "format": {
                    "type": "string",
                    "description": "Gmail only - Message format: 'full' (complete with body), 'metadata' (headers only), 'minimal' (IDs only). Default: 'full'",
                    "default": "full"
                },
                "group_id": {
                    "type": ["string", "null"],
                    "description": "Microsoft only - Microsoft 365 Group ID. If provided, retrieves thread from a Group conversation instead of personal mailbox."
                }
            },
            "required": ["email_address", "thread_id"]
        }
    )
)
def get_thread_messages(
    email_address: str,
    thread_id: str,
    provider: str = "google",
    access_token: Optional[str] = None,
    format: str = "full",
    group_id: Optional[str] = None
) -> str:
    # Auto-fetch access token for Google/Microsoft if not provided
    if provider in ['google', 'microsoft'] and not access_token:
        print(f"Fetching access token for {email_address} to retrieve thread...")
        access_token = _get_access_token_for_email(email_address)
        if not access_token:
            return f"Error: Could not retrieve access token for {email_address}. Please ensure the email is configured in the system."

    return email_service.get_thread_messages(
        thread_id=thread_id,
        provider=provider,
        access_token=access_token,
        format=format,
        group_id=group_id
    )


@tool(
    name_or_callable="forward_email",
    description="""Forward an existing email to one or more recipients. Use this when the user wants to share an email with someone else.

Supported providers: 'google' (Gmail) and 'microsoft' (Outlook/Microsoft 365).
All credentials are automatically retrieved from the system.

When to use this tool:
- User asks to "forward" an email
- User wants to share an email with someone
- User says "send this to..." referring to an existing email

IMPORTANT: You MUST first use search_emails or retrieve_last_n_emails to get a valid message_id. Do NOT make up or guess message IDs - they must come from actual email data.

Workflow:
1. First use search_emails to find the email
2. Get the message_id from the results
3. Use this tool with the message_id and recipient list

Returns: A confirmation message indicating the email was forwarded successfully.""",
    args_schema=(
        {
            "type": "object",
            "properties": {
                "email_address": {
                    "type": "string",
                    "description": "The email address to forward from. Must be configured in the system."
                },
                "message_id": {
                    "type": "string",
                    "description": "The ID of the message to forward. MUST be obtained from search_emails or retrieve_last_n_emails results."
                },
                "to_recipients": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of email addresses to forward the message to (e.g., ['colleague@company.com', 'team@company.com'])."
                },
                "provider": {
                    "type": "string",
                    "description": "Email provider: 'google' for Gmail, 'microsoft' for Outlook/M365. Default: 'google'",
                    "default": "google"
                },
                "access_token": {
                    "type": ["string", "null"],
                    "description": "OAuth access token. Leave empty - automatically retrieved."
                },
                "comment": {
                    "type": ["string", "null"],
                    "description": "Optional comment to add at the top of the forwarded email (e.g., 'FYI - please review this.')."
                }
            },
            "required": ["email_address", "message_id", "to_recipients"]
        }
    )
)
def forward_email(
    email_address: str,
    message_id: str,
    to_recipients: List[str],
    provider: str = "google",
    access_token: Optional[str] = None,
    comment: Optional[str] = None
) -> str:
    # Auto-fetch access token for Google/Microsoft if not provided
    if provider in ['google', 'microsoft'] and not access_token:
        print(f"Fetching access token for {email_address} to forward email...")
        access_token = _get_access_token_for_email(email_address)
        if not access_token:
            return f"Error: Could not retrieve access token for {email_address}. Please ensure the email is configured in the system."

    return email_service.forward_email(
        message_id=message_id,
        to_recipients=to_recipients,
        provider=provider,
        access_token=access_token,
        comment=comment
    )


@tool(
    name_or_callable="reply_to_email",
    description="""Reply to an existing email. Can reply to just the sender or to all recipients (reply all).

Supported providers: 'google' (Gmail), 'microsoft' (Outlook/Microsoft 365), and 'imap' (generic IMAP/SMTP servers).
All credentials are automatically retrieved from the system.

When to use this tool:
- User wants to reply to an email
- User says "respond to...", "answer...", or "reply to..."
- User wants to continue an email conversation

IMPORTANT: You MUST first use search_emails or retrieve_last_n_emails to get a valid message_id. Do NOT make up or guess message IDs - they must come from actual email data.

Workflow:
1. First use search_emails or retrieve_last_n_emails to find the email
2. Get the message_id from the results
3. Use this tool with the message_id and reply content

Returns: A confirmation message indicating the reply was sent successfully.""",
    args_schema=(
        {
            "type": "object",
            "properties": {
                "email_address": {
                    "type": "string",
                    "description": "The email address to reply from. Must be configured in the system."
                },
                "message_id": {
                    "type": "string",
                    "description": "The ID of the message to reply to. MUST be obtained from search_emails or retrieve_last_n_emails results."
                },
                "body": {
                    "type": "string",
                    "description": "The reply message content. This is the text that will be sent as the reply."
                },
                "provider": {
                    "type": "string",
                    "description": "Email provider: 'google' for Gmail, 'microsoft' for Outlook/M365, 'imap' for other providers. Default: 'google'",
                    "default": "google"
                },
                "access_token": {
                    "type": ["string", "null"],
                    "description": "OAuth access token. Leave empty - automatically retrieved."
                },
                "reply_all": {
                    "type": "boolean",
                    "description": "If true, reply to all recipients (sender + To + Cc). If false, reply only to sender. Default: false",
                    "default": False
                },
                "additional_recipients": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "description": "Optional list of additional email addresses to include in the reply (e.g., ['manager@company.com'])."
                }
            },
            "required": ["email_address", "message_id", "body"]
        }
    )
)
def reply_to_email(
    email_address: str,
    message_id: str,
    body: str,
    provider: str = "google",
    access_token: Optional[str] = None,
    reply_all: bool = False,
    additional_recipients: Optional[List[str]] = None
) -> str:
    # Auto-fetch access token for Google/Microsoft if not provided
    if provider in ['google', 'microsoft'] and not access_token:
        print(f"Fetching access token for {email_address} to reply to email...")
        access_token = _get_access_token_for_email(email_address)
        if not access_token:
            return f"Error: Could not retrieve access token for {email_address}. Please ensure the email is configured in the system."

        return email_service.reply_to_email(
            message_id=message_id,
            body=body,
            provider=provider,
            access_token=access_token,
            reply_all=reply_all,
            additional_recipients=additional_recipients
        )
    
    # Auto-fetch IMAP/SMTP credentials if provider is 'imap'
    if provider == 'imap':
        print(f"Fetching IMAP/SMTP credentials for {email_address} to reply to email...")
        credentials = _get_imap_smtp_credentials(email_address)
        if not credentials:
            return f"Error: Could not retrieve IMAP/SMTP credentials for {email_address}. Please ensure the email is configured with IMAP/SMTP settings."
        
        return email_service.reply_to_email(
            message_id=message_id,
            body=body,
            provider=provider,
            reply_all=reply_all,
            additional_recipients=additional_recipients,
            imap_host=credentials["imap_host"],
            smtp_host=credentials["smtp_host"],
            username=credentials["email"],
            password=credentials["password"],
            imap_port=credentials["imap_port"],
            smtp_port=credentials["smtp_port"]
        )
    
    return f"Error: Unsupported provider '{provider}'. Use 'google', 'microsoft', or 'imap'."


@tool(
    name_or_callable="delete_emails",
    description="""Permanently delete one or more emails. THIS ACTION CANNOT BE UNDONE.

Supported providers: 'google' (Gmail), 'microsoft' (Outlook/Microsoft 365), and 'imap' (generic IMAP servers).
All credentials are automatically retrieved from the system.

When to use this tool:
- User explicitly asks to delete emails
- User wants to remove unwanted emails
- User says "delete", "remove", or "trash" referring to emails

IMPORTANT SAFETY RULES:
1. You MUST first use search_emails or retrieve_last_n_emails to get valid message_ids
2. Do NOT make up or guess message IDs - they must come from actual email data
3. ALWAYS confirm with the user before deleting - show them which emails will be deleted
4. This action is PERMANENT and cannot be undone

Workflow:
1. First use search_emails to find the emails to delete
2. Show the user which emails will be deleted and get explicit confirmation
3. Only then use this tool with the message_ids

Returns: A confirmation message indicating how many emails were deleted.""",
    args_schema=(
        {
            "type": "object",
            "properties": {
                "email_address": {
                    "type": "string",
                    "description": "The email address to delete emails from. Must be configured in the system."
                },
                "message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of message IDs to delete. MUST be obtained from search_emails or retrieve_last_n_emails results. For Gmail: hexadecimal strings. For Microsoft: message id strings. For IMAP: sequence numbers."
                },
                "provider": {
                    "type": "string",
                    "description": "Email provider: 'google' for Gmail, 'microsoft' for Outlook/M365, 'imap' for other providers. Default: 'google'",
                    "default": "google"
                },
                "access_token": {
                    "type": ["string", "null"],
                    "description": "OAuth access token. Leave empty - automatically retrieved for google/microsoft providers."
                }
            },
            "required": ["email_address", "message_ids"]
        }
    )
)
def delete_emails(
    email_address: str,
    message_ids: List[str],
    provider: str = "google",
    access_token: Optional[str] = None
) -> str:
    # Auto-fetch access token for Google/Microsoft if not provided
    if provider in ['google', 'microsoft'] and not access_token:
        print(f"Fetching access token for {email_address} to delete emails...")
        access_token = _get_access_token_for_email(email_address)
        if not access_token:
            return f"Error: Could not retrieve access token for {email_address}. Please ensure the email is configured in the system."

        return email_service.delete_emails(
            message_ids=message_ids,
            provider=provider,
            access_token=access_token
        )
    
    # Auto-fetch IMAP credentials if provider is 'imap'
    if provider == 'imap':
        print(f"Fetching IMAP credentials for {email_address} to delete emails...")
        credentials = _get_imap_smtp_credentials(email_address)
        if not credentials:
            return f"Error: Could not retrieve IMAP credentials for {email_address}. Please ensure the email is configured with IMAP/SMTP settings."
        
        return email_service.delete_emails(
            message_ids=message_ids,
            provider=provider,
            host=credentials["imap_host"],
            username=credentials["email"],
            password=credentials["password"],
            port=credentials["imap_port"]
        )
    
    return f"Error: Unsupported provider '{provider}'. Use 'google', 'microsoft', or 'imap'."


@tool(
    name_or_callable="schedule_or_propose_meeting",
    description="""Schedule a meeting or propose available time slots for a meeting. This tool handles both single-person and multi-person meeting scheduling.

USE CASES:
1. Schedule a meeting for just the user (no colleagues)
2. Schedule a meeting with colleagues from the same company
3. Propose available time slots when no specific time is provided

WORKFLOW:
1. If colleagues are specified by NAME and multiple matches are found (ambiguous), the tool returns immediately asking for clarification
2. If colleagues are specified but not found, the tool returns an error
3. If all participants are identified:
   - Without preferred_datetime: Returns a list of free slots in common
   - With preferred_datetime: Checks availability and creates the event if everyone is free, otherwise proposes alternatives

IMPORTANT:
- The sender_email must be a configured email in the system with calendar access
- Colleagues are searched within the same company (subscription) only
- Business hours of all participants are respected (common availability window)
- The tool searches up to days_ahead days into the future (default: 10)

Returns: A message with either the proposed time slots, a confirmation of the created event, or an error/clarification request.""",
    args_schema=(
        {
            "type": "object",
            "properties": {
                "sender_email": {
                    "type": "string",
                    "description": "Email address of the meeting organizer. Must be configured in the system with calendar access."
                },
                "event_title": {
                    "type": "string",
                    "description": "Title/subject of the meeting event."
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration of the meeting in minutes (e.g., 30, 60, 90).",
                    "default": 60
                },
                "colleagues_names_or_emails": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "description": "Optional list of colleague names or emails to include in the meeting. Names are searched within the same company. Leave empty for personal events."
                },
                "preferred_datetime": {
                    "type": ["string", "null"],
                    "description": "Optional ISO format datetime for the preferred meeting time (e.g., '2024-03-15T10:00:00'). If provided and available, the event will be created. If not available, alternatives will be proposed."
                },
                "days_ahead": {
                    "type": "integer",
                    "description": "Number of days to search ahead for available slots. Default: 10",
                    "default": 10
                },
                "event_description": {
                    "type": ["string", "null"],
                    "description": "Optional description/notes for the meeting."
                },
                "event_location": {
                    "type": ["string", "null"],
                    "description": "Optional location for the meeting (e.g., 'Conference Room A', 'Google Meet')."
                }
            },
            "required": ["sender_email", "event_title", "duration_minutes"]
        }
    )
)
def schedule_or_propose_meeting(
    sender_email: str,
    event_title: str,
    duration_minutes: int = 60,
    colleagues_names_or_emails: Optional[List[str]] = None,
    preferred_datetime: Optional[str] = None,
    days_ahead: int = 10,
    event_description: Optional[str] = None,
    event_location: Optional[str] = None
) -> str:
    """
    Schedule a meeting or propose available time slots based on calendar availability.
    """
    print(f"🗓️ [MEETING] Starting schedule_or_propose_meeting for {sender_email}")
    print(f"   Title: {event_title}, Duration: {duration_minutes}min")
    print(f"   Colleagues: {colleagues_names_or_emails}")
    print(f"   Preferred: {preferred_datetime}, Days ahead: {days_ahead}")
    
    # Step 1: Get organizer's calendar info
    organizer_info = get_user_calendar_info(sender_email)
    if not organizer_info:
        return f"Errore: Non è stato possibile trovare le informazioni del calendario per {sender_email}. Assicurati che l'email sia configurata nel sistema con accesso al calendario."
    
    if not organizer_info.get("hashed_access_token"):
        return f"Errore: L'utente {sender_email} non ha un token di accesso al calendario configurato."
    
    if not organizer_info.get("calendar_provider"):
        return f"Errore: L'utente {sender_email} non ha un provider calendario configurato (google/microsoft)."
    
    # Build participants list starting with organizer
    participants = [organizer_info]
    attendee_emails = []
    
    # Step 2: If colleagues are specified, resolve them
    if colleagues_names_or_emails:
        print(f"🔍 [MEETING] Searching for colleagues: {colleagues_names_or_emails}")
        
        colleagues_result = get_colleagues_by_subscription(sender_email, colleagues_names_or_emails)
        
        # Check for errors
        if colleagues_result.get("error"):
            return f"Errore nella ricerca dei colleghi: {colleagues_result['error']}"
        
        # Check for ambiguous matches (STOP immediately)
        ambiguous = colleagues_result.get("ambiguous_matches", {})
        if ambiguous:
            ambiguous_msgs = []
            for term, emails in ambiguous.items():
                emails_list = ", ".join(emails)
                ambiguous_msgs.append(f"'{term}' corrisponde a più colleghi: [{emails_list}]")
            
            return (
                f"⚠️ Ambiguità trovata! Non posso procedere perché alcuni nomi corrispondono a più persone:\n"
                f"{chr(10).join(ambiguous_msgs)}\n\n"
                f"Per favore, chiedi all'utente di specificare l'email esatta del collega desiderato."
            )
        
        # Check for not found terms
        not_found = colleagues_result.get("not_found", [])
        if not_found:
            not_found_list = ", ".join(not_found)
            return (
                f"⚠️ Non trovato! Non sono riuscito a trovare i seguenti colleghi nella stessa azienda:\n"
                f"[{not_found_list}]\n\n"
                f"Verifica che i nomi o le email siano corretti, oppure che i colleghi siano configurati nel sistema."
            )
        
        # Add exact matches to participants
        exact_matches = colleagues_result.get("exact_matches", [])
        for colleague in exact_matches:
            if colleague.get("email") and colleague.get("email") != sender_email:
                participants.append(colleague)
                attendee_emails.append(colleague.get("email"))
        
        print(f"✅ [MEETING] Found {len(exact_matches)} colleagues")
    
    # Step 3: If preferred_datetime is provided, check availability and create event
    if preferred_datetime:
        print(f"📅 [MEETING] Checking availability for preferred time: {preferred_datetime}")
        
        availability = check_slot_availability(
            participants=participants,
            slot_datetime=preferred_datetime,
            duration_minutes=duration_minutes
        )
        
        # Check for errors
        if availability.get("error"):
            return f"Errore nel controllo disponibilità: {availability['error']}"
        
        # Warn about calendar errors but continue
        calendar_errors = availability.get("calendar_errors", [])
        if calendar_errors:
            errors_list = ", ".join(calendar_errors)
            print(f"⚠️ [MEETING] Could not access calendars for: {errors_list}")
        
        # If slot is available, create the event
        if availability.get("available"):
            print(f"✅ [MEETING] Slot available, creating event...")
            
            event_result = schedule_calendar_event(
                organizer=organizer_info,
                title=event_title,
                start_datetime=preferred_datetime,
                duration_minutes=duration_minutes,
                attendees=attendee_emails if attendee_emails else None,
                description=event_description,
                location=event_location
            )
            
            if event_result.get("success"):
                attendees_msg = f" con {', '.join(attendee_emails)}" if attendee_emails else ""
                return (
                    f"✅ Evento creato con successo!\n"
                    f"📅 Titolo: {event_title}\n"
                    f"🕐 Quando: {preferred_datetime}\n"
                    f"⏱️ Durata: {duration_minutes} minuti{attendees_msg}\n"
                    f"🆔 ID evento: {event_result.get('event_id')}"
                )
            else:
                return f"Errore nella creazione dell'evento: {event_result.get('error', 'Errore sconosciuto')}"
        
        # Slot not available - find alternatives
        conflicts = availability.get("conflicts", [])
        conflicts_msg = f" (Conflitti: {', '.join(conflicts)})" if conflicts else ""
        
        print(f"⚠️ [MEETING] Slot not available{conflicts_msg}, finding alternatives...")
        
        # Find alternative slots
        free_result = find_common_free_slots(
            participants=participants,
            duration_minutes=duration_minutes,
            days_ahead=days_ahead,
            preferred_datetime=None  # Search all available days
        )
        
        if free_result.get("error"):
            return f"L'orario richiesto ({preferred_datetime}) non è disponibile{conflicts_msg}. Errore nella ricerca alternative: {free_result['error']}"
        
        free_slots = free_result.get("free_slots", [])
        if not free_slots:
            return (
                f"⚠️ L'orario richiesto ({preferred_datetime}) non è disponibile{conflicts_msg}.\n"
                f"Purtroppo non ho trovato slot liberi comuni nei prossimi {days_ahead} giorni.\n"
                f"Prova ad estendere il periodo di ricerca o a ridurre la durata della riunione."
            )
        
        # Format alternative slots (show max 5)
        slots_display = free_slots[:5]
        slots_formatted = "\n".join([f"  • {slot}" for slot in slots_display])
        more_msg = f"\n  ...e altri {len(free_slots) - 5} slot disponibili" if len(free_slots) > 5 else ""
        
        return (
            f"⚠️ L'orario richiesto ({preferred_datetime}) non è disponibile{conflicts_msg}.\n\n"
            f"Ecco alcuni slot alternativi disponibili per tutti i partecipanti:\n"
            f"{slots_formatted}{more_msg}\n\n"
            f"Chiedi all'utente quale preferisce, poi richiama questo tool con quel preferred_datetime."
        )
    
    # Step 4: No preferred datetime - just propose available slots
    print(f"🔍 [MEETING] No preferred time, finding available slots...")
    
    free_result = find_common_free_slots(
        participants=participants,
        duration_minutes=duration_minutes,
        days_ahead=days_ahead
    )
    
    if free_result.get("error"):
        return f"Errore nella ricerca degli slot disponibili: {free_result['error']}"
    
    # Warn about calendar errors
    calendar_errors = free_result.get("calendar_errors", [])
    errors_warning = ""
    if calendar_errors:
        errors_list = ", ".join(calendar_errors)
        errors_warning = f"\n⚠️ Nota: Non sono riuscito ad accedere ai calendari di: {errors_list}\n"
    
    free_slots = free_result.get("free_slots", [])
    if not free_slots:
        participants_msg = ""
        if len(participants) > 1:
            participant_names = [p.get("name") or p.get("email") for p in participants]
            participants_msg = f" per {', '.join(participant_names)}"
        
        return (
            f"Non ho trovato slot liberi comuni{participants_msg} nei prossimi {days_ahead} giorni.{errors_warning}\n"
            f"Prova ad:\n"
            f"  • Estendere il periodo di ricerca (days_ahead più alto)\n"
            f"  • Ridurre la durata della riunione\n"
            f"  • Verificare che gli orari di lavoro siano configurati correttamente"
        )
    
    # Format available slots (show max 8)
    slots_display = free_slots[:8]
    slots_formatted = "\n".join([f"  • {slot}" for slot in slots_display])
    more_msg = f"\n  ...e altri {len(free_slots) - 8} slot disponibili" if len(free_slots) > 8 else ""
    
    participants_msg = ""
    if len(participants) > 1:
        participant_names = [p.get("name") or p.get("email") for p in participants[1:]]  # Skip organizer
        participants_msg = f" con {', '.join(participant_names)}"
    
    return (
        f"📅 Ecco gli slot disponibili{participants_msg} nei prossimi {days_ahead} giorni:\n\n"
        f"{slots_formatted}{more_msg}{errors_warning}\n\n"
        f"Chiedi all'utente quale preferisce, poi richiama questo tool con quel preferred_datetime per creare l'evento."
    )


@tool(
    name_or_callable="search_email_attachments",
    description=(
        "Search and retrieve attached documents and files sent by a specific email address. "
        "Use this tool when the user asks to find attachments, documents, files, or any material "
        "received from a particular sender or person. Returns a formatted list with download links."
    ),
    args_schema={
        "type": "object",
        "properties": {
            "sender_email": {
                "type": "string",
                "description": "The email address of the sender to search attachments from"
            },
            "user_email": {
                "type": "string",
                "description": "The email address of the current user (from which to retrieve configured mailboxes)"
            }
        },
        "required": ["sender_email", "user_email"]
    }
)
def search_email_attachments(sender_email: str, user_email: str) -> str:
    """
    Search for email attachments from a specific sender.
    
    This tool searches through the user's configured email accounts to find
    all attachments received from a specific sender email address.
    
    Args:
        sender_email: The email address of the sender to search for
        user_email: The current user's email address (to get their configured mailboxes)
        
    Returns:
        Markdown formatted string with:
        - Message if no emails found from sender
        - Message if emails found but no attachments
        - Bullet list with clickable download links if attachments found
    """
    from automations.chatbot.db.db import get_attachments_by_sender_email, get_user_context
    from automations.chatbot.services.documents_service import format_attachments_response
    
    print(f"🔍 [SEARCH_ATTACHMENTS] Searching attachments from {sender_email} for user {user_email}")
    
    # Validate input
    if not sender_email or not sender_email.strip():
        return "Errore: Devi specificare l'indirizzo email del mittente da cercare."
    
    if not user_email or not user_email.strip():
        return "Errore: Non è stato possibile identificare il tuo account email."
    
    # Step 1: Get user's configured email addresses
    try:
        supabase = get_supabase_client()
        
        # Get the user's subscription_id from their email
        user_response = supabase.table("subscription_services").select(
            "subscription_id"
        ).eq("email", user_email.lower().strip()).execute()
        
        if not user_response.data:
            return f"Errore: Non trovo un account configurato per {user_email}."
        
        subscription_id = user_response.data[0].get("subscription_id")
        
        # Get all configured emails for this subscription
        services_response = supabase.table("subscription_services").select(
            "email"
        ).eq("subscription_id", subscription_id).eq("activated", True).execute()
        
        if not services_response.data:
            return "Errore: Non hai caselle email configurate."
        
        user_configured_emails = [s.get("email") for s in services_response.data if s.get("email")]
        
        if not user_configured_emails:
            return "Errore: Non hai caselle email attive."
        
        print(f"✅ [SEARCH_ATTACHMENTS] Found {len(user_configured_emails)} configured emails for user")
        
    except Exception as e:
        print(f"❌ [SEARCH_ATTACHMENTS] Error getting user context: {str(e)}")
        return "Errore nel recupero delle tue caselle email configurate."
    
    # Step 2: Search for attachments from the sender
    try:
        db_result = get_attachments_by_sender_email(
            target_sender_email=sender_email.strip(),
            user_configured_emails=user_configured_emails
        )
        
        # Step 3: Format the response using the service
        formatted_response = format_attachments_response(
            db_result=db_result,
            target_sender_email=sender_email.strip()
        )
        
        return formatted_response
        
    except Exception as e:
        print(f"❌ [SEARCH_ATTACHMENTS] Error searching attachments: {str(e)}")
        return f"Errore nella ricerca degli allegati: {str(e)}"
