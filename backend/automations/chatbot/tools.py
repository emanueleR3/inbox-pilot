from langchain.tools import tool
from typing import Optional, List
from services import email_service
from db.db import get_supabase_client
import os
from cryptography.fernet import Fernet
import base64
import hashlib
import httpx
from datetime import datetime, timedelta

def _get_cipher():
    """Get Fernet cipher for token decryption."""
    encryption_key_str = os.getenv("ENCRYPTION_KEY_TOKEN")
    if not encryption_key_str:
        raise ValueError("ENCRYPTION_KEY_TOKEN not found in environment variables")
    
    encryption_key = encryption_key_str.encode()
    key_hash = hashlib.sha256(encryption_key).digest()
    fernet_key = base64.urlsafe_b64encode(key_hash)
    return Fernet(fernet_key)

def _decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted token."""
    if not encrypted_token:
        return ""
    cipher = _get_cipher()
    return cipher.decrypt(encrypted_token.encode()).decode()

async def _get_access_token_for_email(email: str) -> Optional[str]:
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
        
        # Check if token is expired or expiring soon (within 5 minutes)
        expiry_token = user_data.get("expiry_token")
        if expiry_token:
            try:
                expiry_time = datetime.fromisoformat(expiry_token.replace("Z", "+00:00"))
                now = datetime.utcnow().replace(tzinfo=expiry_time.tzinfo)
                time_until_expiry = expiry_time - now
                
                # If token expires in less than 5 minutes, log warning
                if time_until_expiry.total_seconds() < 300:
                    print(f"Warning: Token for {email} is expired or expiring soon. Refresh mechanism not implemented.")
            except Exception as e:
                print(f"Error checking token expiry: {str(e)}")
        
        # Return current access token
        if user_data.get("hashed_access_token"):
            return _decrypt_token(user_data["hashed_access_token"])
        
        return None
    except Exception as e:
        print(f"Error retrieving access token for {email}: {str(e)}")
        return None

@tool
async def send_email(
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
    Send an email using Google OAuth, Microsoft OAuth, or SMTP.
    
    IMPORTANT: Use 'google' provider (default) unless you have specific SMTP credentials.
    For SMTP, you MUST provide both 'host' and 'password' parameters.
    
    Args:
        sender_address: Email address of the sender
        receiver_address: Email address of the recipient
        subject: Email subject
        body: Email body content
        provider: 'google' (default), 'microsoft', or 'smtp'. Use 'google' unless SMTP is required.
        password: Password or app password (REQUIRED for SMTP, not used for google/microsoft)
        host: SMTP host like 'smtp.gmail.com' (REQUIRED for SMTP provider)
        body_type: 'text' or 'html' (default: 'text')
        cc_recipients: List of CC email addresses
        bcc_recipients: List of BCC email addresses
        attachments: List of file paths to attach
        access_token: OAuth access token (automatically retrieved for google/microsoft)
        port: SMTP port like 587 or 465 (optional for SMTP, defaults to 587)
    """
    
    # Auto-fetch access token for Google/Microsoft if not provided
    if provider in ['google', 'microsoft'] and not access_token:
        print(f"Fetching access token for {sender_address}...")
        access_token = await _get_access_token_for_email(sender_address)
        if not access_token:
            return f"Error: Could not retrieve access token for {sender_address}. Please ensure the email is configured in the system."

    return await email_service.send_email(
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