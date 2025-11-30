from langchain.tools import tool
from typing import Optional, List
from automations.chatbot.services import email_service
from automations.chatbot.db.db import get_supabase_client
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
        access_token = _get_access_token_for_email(sender_address)
        if not access_token:
            return f"Error: Could not retrieve access token for {sender_address}. Please ensure the email is configured in the system."

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
    For 'imap' provider, you must supply host, email_address (as username), and password.

    Args:
        email_address: The email address to retrieve emails from (also used as username for IMAP)
        n: Number of emails to retrieve (default: 10, max: 20)
        provider: 'google' (default), 'microsoft', or 'imap'
        access_token: OAuth access token (automatically retrieved for google/microsoft if not provided)
        host: IMAP host like 'imap.gmail.com' (REQUIRED for 'imap' provider)
        password: Email password (REQUIRED for 'imap' provider)
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
    For 'imap' provider, you must supply host, email_address (as username), and password.

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
        host: IMAP host like 'imap.gmail.com' (REQUIRED for 'imap' provider)
        password: Email password (REQUIRED for 'imap' provider)
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

