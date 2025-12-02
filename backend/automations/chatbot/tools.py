from langchain.tools import tool
from typing import Optional, List
from automations.chatbot.services import email_service
from automations.chatbot.db.db import get_supabase_client
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
        print(f"Attempting to decrypt password (encrypted length: {len(encrypted_password)})")
        decrypted = decrypt(encrypted_password, "pass")
        print(f"Password decrypted successfully")
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

@tool
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
    """
    Send an email using Google OAuth, Microsoft OAuth, IMAP/SMTP, or plain SMTP.
    
    IMPORTANT: Use 'google' provider (default) unless you have specific SMTP credentials.
    For 'imap' provider, credentials are automatically retrieved from the system.
    For 'smtp' provider, you MUST provide both 'host' and 'password' parameters.
    
    Args:
        sender_address: Email address of the sender
        receiver_address: Email address of the recipient
        subject: Email subject
        body: Email body content
        provider: 'google' (default), 'microsoft', 'imap', or 'smtp'. 
                  Use 'imap' for configured IMAP/SMTP accounts.
                  Use 'smtp' only with manual host/password credentials.
        password: Password or app password (REQUIRED for 'smtp', auto-retrieved for 'imap')
        host: SMTP host like 'smtp.gmail.com' (REQUIRED for 'smtp', auto-retrieved for 'imap')
        body_type: 'text' or 'html' (default: 'text')
        cc_recipients: List of CC email addresses
        bcc_recipients: List of BCC email addresses
        attachments: List of file paths to attach
        access_token: OAuth access token (automatically retrieved for google/microsoft)
        port: SMTP port like 587 or 465 (optional, defaults to 587)
    """
    
    # Auto-fetch access token for Google/Microsoft if not provided
    if provider in ['google', 'microsoft'] and not access_token:
        print(f"Fetching access token for {sender_address}...")
        access_token = _get_access_token_for_email(sender_address)
        if not access_token:
            return f"Error: Could not retrieve access token for {sender_address}. Please ensure the email is configured in the system."
    
    # Auto-fetch IMAP/SMTP credentials if provider is 'imap'
    if provider == 'imap':
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
    
@tool
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
    """
    Create an email draft using Google or Microsoft providers.

    If `access_token` is not provided for 'google' or 'microsoft', the function
    will attempt to retrieve and decrypt it from storage.
    """
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


@tool
def retrieve_last_n_emails(
    email_address: str,
    n: int = 10,
    provider: str = "google",
    access_token: Optional[str] = None,
    host: Optional[str] = None,
    password: Optional[str] = None,
    port: Optional[int] = 993
) -> str:
    """
    Retrieve the last N emails from a mailbox. Useful for summarization, searching recent conversations, or context gathering.

    For 'google' or 'microsoft' providers, the access token is automatically retrieved if not provided.
    For 'imap' provider, credentials are automatically retrieved from the system if not provided.

    Args:
        email_address: The email address to retrieve emails from (also used as username for IMAP)
        n: Number of emails to retrieve (default: 10, max: 20)
        provider: 'google' (default), 'microsoft', or 'imap'
        access_token: OAuth access token (automatically retrieved for google/microsoft if not provided)
        host: IMAP host like 'imap.gmail.com' (auto-retrieved for configured 'imap' accounts)
        password: Email password (auto-retrieved for configured 'imap' accounts)
        port: IMAP port (default: 993, only used for 'imap' provider)

    Returns:
        A formatted string containing the retrieved emails, ready for LLM processing/summarization.
    """
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


@tool
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
    """
    Search for emails matching specified criteria. Useful for finding specific conversations,
    emails from a particular sender, or messages within a date range.

    For 'google' or 'microsoft' providers, the access token is automatically retrieved if not provided.
    For 'imap' provider, credentials are automatically retrieved from the system if not provided.

    Args:
        email_address: The email address to search in (also used as username for IMAP)
        query: Raw search query (Gmail format: "from:user@example.com is:unread", or keywords)
        sender: Filter by sender email address (e.g., "boss@company.com")
        subject: Filter by subject keywords (e.g., "meeting notes")
        keywords: List of keywords to search for in email body/subject
        after_date: Only return emails after this date (format: YYYY/MM/DD or YYYY-MM-DD)
        before_date: Only return emails before this date (format: YYYY/MM/DD or YYYY-MM-DD)
        provider: 'google' (default), 'microsoft', or 'imap'
        access_token: OAuth access token (automatically retrieved for google/microsoft if not provided)
        label_ids: List of Gmail label IDs to filter by (e.g., ["INBOX", "IMPORTANT"]) - Gmail only
        include_spam_trash: Include spam and trash folders in search results (default: False)
        max_results: Maximum number of results to return (default: 10, max: 50)
        host: IMAP host like 'imap.gmail.com' (auto-retrieved for configured 'imap' accounts)
        password: Email password (auto-retrieved for configured 'imap' accounts)
        port: IMAP port (default: 993, only used for 'imap' provider)

    Returns:
        A formatted string containing matching emails, ready for LLM processing.

    Examples:
        - Search emails from a specific sender: sender="john@example.com"
        - Search by date range: after_date="2024/01/01", before_date="2024/02/01"
        - Search by keywords: keywords=["invoice", "payment"]
        - Raw Gmail query: query="is:unread from:support@company.com"
        - Combine filters: sender="hr@company.com", subject="policy", after_date="2024/06/01"
    """
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


@tool
def get_thread_messages(
    email_address: str,
    thread_id: str,
    provider: str = "google",
    access_token: Optional[str] = None,
    format: str = "full",
    group_id: Optional[str] = None
) -> str:
    """
    Retrieve all messages in an email thread/conversation. Useful for getting the full context
    of a conversation, following up on discussions, or understanding the history of an email exchange.

    IMPORTANT: You must first use search_emails or retrieve_last_n_emails to get valid thread IDs.
    Do NOT make up or guess thread IDs - they must come from actual email data.

    For 'google' or 'microsoft' providers, the access token is automatically retrieved if not provided.

    Args:
        email_address: The email address to retrieve the thread from
        thread_id: The ID of the thread/conversation to retrieve. 
                   MUST be obtained from search_emails or retrieve_last_n_emails results.
                   For Gmail: Thread IDs look like '18abc123def456gh' (hexadecimal string).
                   For Microsoft: Use the conversationId from a message.
        provider: 'google' (default) or 'microsoft'
        access_token: OAuth access token (automatically retrieved if not provided)
        format: Format for messages (Gmail only):
                - 'full': Complete message with body content (default)
                - 'metadata': Only headers and labels, no body
                - 'minimal': Only message IDs and labels
        group_id: Microsoft 365 Group ID (optional). If provided, retrieves thread from a
                  Microsoft 365 Group conversation instead of personal mailbox.

    Returns:
        A formatted string containing all messages in the thread in chronological order,
        ready for LLM processing.

    Workflow:
        1. First, use search_emails to find emails and get their thread IDs
        2. Then, use this tool with the thread_id from the search results
    """
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


@tool
def forward_email(
    email_address: str,
    message_id: str,
    to_recipients: List[str],
    provider: str = "google",
    access_token: Optional[str] = None,
    comment: Optional[str] = None
) -> str:
    """
    Forward an email to one or more recipients.

    IMPORTANT: You must first use search_emails or retrieve_last_n_emails to get valid message IDs.
    Do NOT make up or guess message IDs - they must come from actual email data.

    For 'google' or 'microsoft' providers, the access token is automatically retrieved if not provided.

    Args:
        email_address: The email address to forward from (must be configured in the system)
        message_id: The ID of the message to forward.
                    MUST be obtained from search_emails or retrieve_last_n_emails results.
        to_recipients: List of email addresses to forward the message to
        provider: 'google' (default) or 'microsoft'
        access_token: OAuth access token (automatically retrieved if not provided)
        comment: Optional comment to include at the top of the forwarded message

    Returns:
        A confirmation message indicating the email was forwarded.

    Workflow:
        1. First, use search_emails to find the email you want to forward
        2. Get the message_id from the search results
        3. Use this tool with the message_id and recipient list

    Examples:
        - Forward to one person: to_recipients=["colleague@company.com"]
        - Forward to multiple: to_recipients=["person1@email.com", "person2@email.com"]
        - Forward with comment: comment="FYI - please review this."
    """
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


@tool
def reply_to_email(
    email_address: str,
    message_id: str,
    body: str,
    provider: str = "google",
    access_token: Optional[str] = None,
    reply_all: bool = False,
    additional_recipients: Optional[List[str]] = None
) -> str:
    """
    Reply to an email. Can reply only to the sender or to all recipients.

    IMPORTANT: You must first use search_emails or retrieve_last_n_emails to get valid message IDs.
    Do NOT make up or guess message IDs - they must come from actual email data.

    For 'google' or 'microsoft' providers, the access token is automatically retrieved if not provided.

    Args:
        email_address: The email address to reply from (must be configured in the system)
        message_id: The ID of the message to reply to.
                    MUST be obtained from search_emails or retrieve_last_n_emails results.
        body: The reply message content
        provider: 'google' (default) or 'microsoft'
        access_token: OAuth access token (automatically retrieved if not provided)
        reply_all: If True, reply to all recipients (sender, To, and Cc). 
                   If False (default), reply only to the sender.
        additional_recipients: Optional list of additional email addresses to include in the reply

    Returns:
        A confirmation message indicating the reply was sent.

    Workflow:
        1. First, use search_emails or retrieve_last_n_emails to find the email you want to reply to
        2. Get the message_id from the results
        3. Use this tool with the message_id and your reply message

    Examples:
        - Simple reply: body="Thank you for the information!"
        - Reply all: body="Thanks everyone!", reply_all=True
        - Add recipients: body="Adding John to this thread.", additional_recipients=["john@company.com"]
    """
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


@tool
def delete_emails(
    email_address: str,
    message_ids: List[str],
    provider: str = "google",
    access_token: Optional[str] = None
) -> str:
    """
    Delete one or more emails by their message IDs. This action is PERMANENT and cannot be undone.

    IMPORTANT: 
    - You must first use search_emails or retrieve_last_n_emails to get valid message IDs.
    - Do NOT make up or guess message IDs - they must come from actual email data.
    - Always confirm with the user before deleting emails.

    For 'google' or 'microsoft' providers, the access token is automatically retrieved if not provided.

    Args:
        email_address: The email address to delete emails from
        message_ids: List of message IDs to delete. 
                     MUST be obtained from search_emails or retrieve_last_n_emails results.
                     For Gmail: Message IDs look like '18abc123def456gh' (hexadecimal string).
                     For Microsoft: Use the message id from search/retrieve results.
        provider: 'google' (default) or 'microsoft'
        access_token: OAuth access token (automatically retrieved if not provided)

    Returns:
        A confirmation message indicating how many emails were deleted.

    Workflow:
        1. First, use search_emails to find the emails you want to delete
        2. Show the user which emails will be deleted and get confirmation
        3. Use this tool with the message_ids from the search results

    Examples:
        - Delete a single email: message_ids=["18abc123def456"]
        - Delete multiple emails: message_ids=["18abc123def456", "18xyz789abc123"]
    """
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

