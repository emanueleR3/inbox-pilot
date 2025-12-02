import smtplib
import base64
import mimetypes
import os
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate
from typing import Optional, List
import httpx
import json


class EmailProvider:
    """Base class for email providers."""
    
    def send_email(
        self,
        sender_address: str,
        receiver_address: str,
        subject: str,
        body: str,
        body_type: str = "text",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        raise NotImplementedError
    
    def create_draft(
        self,
        sender_address: str,
        receiver_address: str,
        subject: str,
        body: str,
        body_type: str = "text",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        raise NotImplementedError


class GoogleEmailProvider(EmailProvider):
    """Google Gmail API provider."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://gmail.googleapis.com/gmail/v1"
    
    def _create_message(
        self,
        sender_address: str,
        receiver_address: str,
        subject: str,
        body: str,
        body_type: str = "text",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None
    ) -> str:
        """Create a MIME message and encode it as base64url."""
        message = EmailMessage()
        
        # Set content
        if body_type == "html":
            message.set_content(body, subtype='html')
        else:
            message.set_content(body)
        
        # Set headers
        message["To"] = receiver_address
        message["From"] = sender_address
        message["Subject"] = subject
        
        if cc_recipients:
            message["Cc"] = ", ".join(cc_recipients)
        if bcc_recipients:
            message["Bcc"] = ", ".join(bcc_recipients)
        
        # Add attachments
        if attachments:
            for attachment_path in attachments:
                if os.path.exists(attachment_path):
                    content_type, _ = mimetypes.guess_type(attachment_path)
                    if content_type is None:
                        content_type = 'application/octet-stream'
                    
                    maintype, subtype = content_type.split('/', 1)
                    
                    with open(attachment_path, 'rb') as fp:
                        attachment_data = fp.read()
                    
                    message.add_attachment(
                        attachment_data,
                        maintype=maintype,
                        subtype=subtype,
                        filename=os.path.basename(attachment_path)
                    )
        
        # Encode as base64url
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return encoded_message
    
    def send_email(
        self,
        sender_address: str,
        receiver_address: str,
        subject: str,
        body: str,
        body_type: str = "text",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Send an email using Gmail API."""
        encoded_message = self._create_message(
            sender_address, receiver_address, subject, body,
            body_type, cc_recipients, bcc_recipients, attachments
        )
        
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/users/me/messages/send",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                json={"raw": encoded_message}
            )
            
            if response.status_code == 200:
                result = response.json()
                return f"Email sent successfully. Message ID: {result.get('id')}"
            else:
                raise Exception(f"Failed to send email: {response.text}")
    
    def create_draft(
        self,
        sender_address: str,
        receiver_address: str,
        subject: str,
        body: str,
        body_type: str = "text",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Create a draft email using Gmail API."""
        encoded_message = self._create_message(
            sender_address, receiver_address, subject, body,
            body_type, cc_recipients, bcc_recipients, attachments
        )
        
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/users/me/drafts",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                json={"message": {"raw": encoded_message}}
            )
            
            if response.status_code == 200:
                result = response.json()
                return f"Draft created successfully. Draft ID: {result.get('id')}"
            else:
                raise Exception(f"Failed to create draft: {response.text}")


class MicrosoftEmailProvider(EmailProvider):
    """Microsoft Graph API provider."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0"
    
    def _create_message_body(
        self,
        sender_address: str,
        receiver_address: str,
        subject: str,
        body: str,
        body_type: str = "text",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None
    ) -> dict:
        """Create a message body for Microsoft Graph API."""
        message = {
            "subject": subject,
            "body": {
                "contentType": "HTML" if body_type == "html" else "Text",
                "content": body
            },
            "toRecipients": [
                {"emailAddress": {"address": receiver_address}}
            ]
        }
        
        if cc_recipients:
            message["ccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in cc_recipients
            ]
        
        if bcc_recipients:
            message["bccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in bcc_recipients
            ]
        
        # Note: Attachments for Microsoft Graph require separate API calls
        # This is a simplified version
        if attachments:
            message["hasAttachments"] = True
        
        return message
    
    def send_email(
        self,
        sender_address: str,
        receiver_address: str,
        subject: str,
        body: str,
        body_type: str = "text",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Send an email using Microsoft Graph API."""
        message_body = self._create_message_body(
            sender_address, receiver_address, subject, body,
            body_type, cc_recipients, bcc_recipients, attachments
        )
        
        with httpx.Client() as client:
            # Send mail directly
            response = client.post(
                f"{self.base_url}/me/sendMail",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                json={"message": message_body}
            )
            
            if response.status_code == 202:
                return f"Email sent successfully to {receiver_address}"
            else:
                raise Exception(f"Failed to send email: {response.text}")
    
    def create_draft(
        self,
        sender_address: str,
        receiver_address: str,
        subject: str,
        body: str,
        body_type: str = "text",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Create a draft email using Microsoft Graph API."""
        message_body = self._create_message_body(
            sender_address, receiver_address, subject, body,
            body_type, cc_recipients, bcc_recipients, attachments
        )
        
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/me/messages",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                json=message_body
            )
            
            if response.status_code == 201:
                result = response.json()
                return f"Draft created successfully. Draft ID: {result.get('id')}"
            else:
                raise Exception(f"Failed to create draft: {response.text}")


class SMTPEmailProvider(EmailProvider):
    """SMTP provider for custom email servers."""
    
    def __init__(self, host: str, port: int = 587, username: str = None, password: str = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
    
    def _create_message(
        self,
        sender_address: str,
        receiver_address: str,
        subject: str,
        body: str,
        body_type: str = "text",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None
    ):
        """Create a MIME message."""
        if attachments:
            msg = MIMEMultipart()
        else:
            msg = MIMEMultipart('alternative') if body_type == "html" else MIMEText(body, 'plain')
            if isinstance(msg, MIMEText):
                msg['Subject'] = subject
                msg['From'] = sender_address
                msg['To'] = receiver_address
                msg['Date'] = formatdate(localtime=True)
                if cc_recipients:
                    msg['Cc'] = ', '.join(cc_recipients)
                return msg
        
        msg['Subject'] = subject
        msg['From'] = sender_address
        msg['To'] = receiver_address
        msg['Date'] = formatdate(localtime=True)
        
        if cc_recipients:
            msg['Cc'] = ', '.join(cc_recipients)
        
        # Add body
        if body_type == "html":
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        # Add attachments
        if attachments:
            for attachment_path in attachments:
                if os.path.exists(attachment_path):
                    with open(attachment_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename={os.path.basename(attachment_path)}'
                        )
                        msg.attach(part)
        
        return msg
    
    def send_email(
        self,
        sender_address: str,
        receiver_address: str,
        subject: str,
        body: str,
        body_type: str = "text",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Send an email using SMTP."""
        msg = self._create_message(
            sender_address, receiver_address, subject, body,
            body_type, cc_recipients, bcc_recipients, attachments
        )
        
        all_recipients = [receiver_address]
        if cc_recipients:
            all_recipients.extend(cc_recipients)
        if bcc_recipients:
            all_recipients.extend(bcc_recipients)
        
        
        # Use SMTP_SSL for port 465 (implicit SSL), SMTP + starttls for other ports
        if self.port == 465:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=30) as server:
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(sender_address, all_recipients, msg.as_string())
        else:
            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(sender_address, all_recipients, msg.as_string())
        
        return f"Email sent to {receiver_address} with subject '{subject}'."
    
    def create_draft(
        self,
        sender_address: str,
        receiver_address: str,
        subject: str,
        body: str,
        body_type: str = "text",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """SMTP doesn't support drafts, so this just returns a message."""
        return f"SMTP provider doesn't support drafts. Use send_email instead."


# Main interface functions

def send_email(
    sender_address: str,
    password: str,
    receiver_address: str,
    subject: str,
    body: str,
    provider: str,
    host: str = None,
    body_type: str = "text",
    cc_recipients: Optional[List[str]] = None,
    bcc_recipients: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
    access_token: Optional[str] = None,
    port: Optional[int] = None
) -> str:
    """
    Send an email using the specified provider.
    
    Args:
        sender_address: Email address of the sender
        password: Password or app password (for SMTP)
        receiver_address: Email address of the recipient
        subject: Email subject
        body: Email body content
        provider: 'google', 'microsoft', or 'smtp'
        host: SMTP host (required for SMTP provider)
        body_type: 'text' or 'html'
        cc_recipients: List of CC recipients
        bcc_recipients: List of BCC recipients
        attachments: List of file paths to attach
        access_token: OAuth access token (required for google/microsoft)
    """
    if provider == 'google':
        if not access_token:
            raise ValueError("access_token is required for Google provider")
        email_provider = GoogleEmailProvider(access_token)
    elif provider == 'microsoft':
        if not access_token:
            raise ValueError("access_token is required for Microsoft provider")
        email_provider = MicrosoftEmailProvider(access_token)
    elif provider == 'smtp':
        if not host:
            raise ValueError("host is required for SMTP provider")
        email_provider = SMTPEmailProvider(host, username=sender_address, password=password, port=port)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    
    return email_provider.send_email(
        sender_address, receiver_address, subject, body,
        body_type, cc_recipients, bcc_recipients, attachments
    )


def create_draft(
    sender_address: str,
    receiver_address: str,
    subject: str,
    body: str,
    provider: str,
    access_token: str,
    body_type: str = "text",
    cc_recipients: Optional[List[str]] = None,
    bcc_recipients: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None
) -> str:
    """
    Create a draft email using the specified provider.
    
    Args:
        sender_address: Email address of the sender
        receiver_address: Email address of the recipient
        subject: Email subject
        body: Email body content
        provider: 'google' or 'microsoft'
        access_token: OAuth access token
        body_type: 'text' or 'html'
        cc_recipients: List of CC recipients
        bcc_recipients: List of BCC recipients
        attachments: List of file paths to attach
    """
    if provider == 'google':
        email_provider = GoogleEmailProvider(access_token)
    elif provider == 'microsoft':
        email_provider = MicrosoftEmailProvider(access_token)
    else:
        raise ValueError(f"Provider {provider} doesn't support drafts")
    
    return email_provider.create_draft(
        sender_address, receiver_address, subject, body,
        body_type, cc_recipients, bcc_recipients, attachments
    )


def retrieve_last_n_emails(
    n: int,
    provider: str,
    access_token: Optional[str] = None,
    host: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    port: Optional[int] = 993
) -> str:
    """
    Retrieve the last N emails from the specified provider.
    
    Args:
        n: Number of emails to retrieve
        provider: 'google', 'microsoft', or 'imap'
        access_token: OAuth access token (required for google/microsoft)
        host: IMAP host (required for IMAP provider)
        username: Email username (required for IMAP)
        password: Email password (required for IMAP)
        port: IMAP port (default: 993)
    
    Returns:
        String containing email data formatted for LLM processing
    """
    if provider == 'google':
        if not access_token:
            raise ValueError("access_token is required for Google provider")
        return _retrieve_gmail_emails(access_token, n)
    elif provider == 'microsoft':
        if not access_token:
            raise ValueError("access_token is required for Microsoft provider")
        return _retrieve_microsoft_emails(access_token, n)
    elif provider == 'imap':
        if not host or not username or not password:
            raise ValueError("host, username, and password are required for IMAP provider")
        return _retrieve_imap_emails(host, port, username, password, n)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def search_emails(
    provider: str,
    access_token: Optional[str] = None,
    query: Optional[str] = None,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    after_date: Optional[str] = None,
    before_date: Optional[str] = None,
    label_ids: Optional[List[str]] = None,
    include_spam_trash: bool = False,
    max_results: int = 10,
    host: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    port: Optional[int] = 993
) -> str:
    """
    Search for emails matching specified criteria.
    
    Args:
        provider: 'google', 'microsoft', or 'imap'
        access_token: OAuth access token (required for google/microsoft)
        query: Raw query string (Gmail format for google, OData for microsoft)
        sender: Filter by sender email address
        subject: Filter by subject keywords
        keywords: List of keywords to search for in email body/subject
        after_date: Only return emails after this date (YYYY/MM/DD or YYYY-MM-DD)
        before_date: Only return emails before this date (YYYY/MM/DD or YYYY-MM-DD)
        label_ids: List of label IDs to filter by (Gmail only)
        include_spam_trash: Include spam and trash in results
        max_results: Maximum number of results (default: 10, max: 50)
        host: IMAP host (required for IMAP provider)
        username: Email username (required for IMAP)
        password: Email password (required for IMAP)
        port: IMAP port (default: 993)
    
    Returns:
        String containing matching emails formatted for LLM processing
    """
    max_results = min(max_results, 50)  # Cap at 50
    
    if provider == 'google':
        if not access_token:
            raise ValueError("access_token is required for Google provider")
        return _search_gmail_emails(
            access_token=access_token,
            query=query,
            sender=sender,
            subject=subject,
            keywords=keywords,
            after_date=after_date,
            before_date=before_date,
            label_ids=label_ids,
            include_spam_trash=include_spam_trash,
            max_results=max_results
        )
    elif provider == 'microsoft':
        if not access_token:
            raise ValueError("access_token is required for Microsoft provider")
        return _search_microsoft_emails(
            access_token=access_token,
            query=query,
            sender=sender,
            subject=subject,
            keywords=keywords,
            after_date=after_date,
            before_date=before_date,
            max_results=max_results
        )
    elif provider == 'imap':
        if not host or not username or not password:
            raise ValueError("host, username, and password are required for IMAP provider")
        return _search_imap_emails(
            host=host,
            port=port,
            username=username,
            password=password,
            sender=sender,
            subject=subject,
            keywords=keywords,
            after_date=after_date,
            before_date=before_date,
            max_results=max_results
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def delete_emails(
    message_ids: List[str],
    provider: str,
    access_token: str
) -> str:
    """
    Delete emails by their message IDs.
    
    Args:
        message_ids: List of message IDs to delete
        provider: 'google' or 'microsoft'
        access_token: OAuth access token
    
    Returns:
        String confirming deletion or error message
    """
    if not message_ids:
        return "Error: No message IDs provided for deletion."
    
    if provider == 'google':
        return _delete_gmail_emails(access_token, message_ids)
    elif provider == 'microsoft':
        return _delete_microsoft_emails(access_token, message_ids)
    else:
        raise ValueError(f"Provider {provider} doesn't support email deletion")


def forward_email(
    message_id: str,
    to_recipients: List[str],
    provider: str,
    access_token: str,
    comment: Optional[str] = None
) -> str:
    """
    Forward an email to one or more recipients.
    
    Args:
        message_id: The ID of the message to forward
        to_recipients: List of email addresses to forward to
        provider: 'google' or 'microsoft'
        access_token: OAuth access token
        comment: Optional comment to include with the forwarded message
    
    Returns:
        String confirming the forward or error message
    """
    if not message_id:
        return "Error: No message ID provided."
    
    if not to_recipients:
        return "Error: No recipients provided for forwarding."
    
    if provider == 'google':
        return _forward_gmail_email(access_token, message_id, to_recipients, comment)
    elif provider == 'microsoft':
        return _forward_microsoft_email(access_token, message_id, to_recipients, comment)
    else:
        raise ValueError(f"Provider {provider} doesn't support email forwarding")


def reply_to_email(
    message_id: str,
    body: str,
    provider: str,
    access_token: str,
    reply_all: bool = False,
    additional_recipients: Optional[List[str]] = None
) -> str:
    """
    Reply to an email.
    
    Args:
        message_id: The ID of the message to reply to
        body: The reply message body/comment
        provider: 'google' or 'microsoft'
        access_token: OAuth access token
        reply_all: If True, reply to all recipients (default: False, reply only to sender)
        additional_recipients: Optional list of additional recipients to include in the reply
    
    Returns:
        String confirming the reply or error message
    """
    if not message_id:
        return "Error: No message ID provided."
    
    if not body:
        return "Error: Reply body/comment is required."
    
    if provider == 'google':
        return _reply_gmail_email(access_token, message_id, body, reply_all, additional_recipients)
    elif provider == 'microsoft':
        return _reply_microsoft_email(access_token, message_id, body, reply_all, additional_recipients)
    else:
        raise ValueError(f"Provider {provider} doesn't support email replies")


def get_thread_messages(
    thread_id: str,
    provider: str,
    access_token: str,
    format: str = "full",
    group_id: Optional[str] = None
) -> str:
    """
    Retrieve all messages in an email thread/conversation.
    
    Args:
        thread_id: The ID of the thread to retrieve
        provider: 'google' or 'microsoft'
        access_token: OAuth access token
        format: Format for messages - 'full', 'metadata', or 'minimal' (Gmail only)
        group_id: Microsoft 365 Group ID (optional, for group conversations)
    
    Returns:
        String containing all messages in the thread formatted for LLM processing
    """
    if provider == 'google':
        return _get_gmail_thread(access_token, thread_id, format)
    elif provider == 'microsoft':
        return _get_microsoft_conversation(access_token, thread_id, group_id)
    else:
        raise ValueError(f"Provider {provider} doesn't support thread retrieval")


def _forward_microsoft_email(access_token: str, message_id: str, to_recipients: List[str], comment: Optional[str] = None) -> str:
    """
    Forward an email using Microsoft Graph API.
    
    Uses: POST /me/messages/{id}/forward
    """
    base_url = "https://graph.microsoft.com/v1.0"
    
    # Build the request body
    request_body = {
        "toRecipients": [
            {"emailAddress": {"address": recipient.strip()}}
            for recipient in to_recipients if recipient and recipient.strip()
        ]
    }
    
    if comment:
        request_body["comment"] = comment
    
    with httpx.Client() as client:
        response = client.post(
            f"{base_url}/me/messages/{message_id}/forward",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=request_body
        )
        
        if response.status_code == 202:
            recipients_str = ", ".join(to_recipients)
            return f"Email successfully forwarded to: {recipients_str}"
        elif response.status_code == 400:
            return f"Error: Invalid request. The message ID may be invalid or the request body is malformed. Details: {response.text}"
        elif response.status_code == 401:
            return "Error: Authentication failed. The access token may be expired or invalid."
        elif response.status_code == 403:
            return "Error: Permission denied. The app may not have permission to send emails."
        elif response.status_code == 404:
            return f"Error: Message not found with ID '{message_id}'."
        else:
            return f"Error: Failed to forward email. Status: {response.status_code}. Details: {response.text}"


def _reply_microsoft_email(
    access_token: str,
    message_id: str,
    comment: str,
    reply_all: bool = False,
    additional_recipients: Optional[List[str]] = None
) -> str:
    """
    Reply to an email using Microsoft Graph API.
    
    Uses: POST /me/messages/{id}/reply or POST /me/messages/{id}/replyAll
    """
    base_url = "https://graph.microsoft.com/v1.0"
    
    # Choose endpoint based on reply_all
    endpoint = "replyAll" if reply_all else "reply"
    
    # Build the request body
    request_body = {
        "comment": comment
    }
    
    # Add additional recipients if provided
    if additional_recipients:
        request_body["message"] = {
            "toRecipients": [
                {"emailAddress": {"address": recipient.strip()}}
                for recipient in additional_recipients if recipient and recipient.strip()
            ]
        }
    
    with httpx.Client() as client:
        response = client.post(
            f"{base_url}/me/messages/{message_id}/{endpoint}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=request_body
        )
        
        if response.status_code == 202:
            reply_type = "all recipients" if reply_all else "sender"
            return f"Reply successfully sent to {reply_type}."
        elif response.status_code == 400:
            return f"Error: Invalid request. The message ID may be invalid or the request body is malformed. Details: {response.text}"
        elif response.status_code == 401:
            return "Error: Authentication failed. The access token may be expired or invalid."
        elif response.status_code == 403:
            return "Error: Permission denied. The app may not have permission to send emails."
        elif response.status_code == 404:
            return f"Error: Message not found with ID '{message_id}'."
        else:
            return f"Error: Failed to send reply. Status: {response.status_code}. Details: {response.text}"


def _forward_gmail_email(access_token: str, message_id: str, to_recipients: List[str], comment: Optional[str] = None) -> str:
    """
    Forward an email using Gmail API.
    
    Gmail doesn't have a native forward endpoint, so we:
    1. Get the original message
    2. Create a new message with forwarded content
    3. Send the new message
    """
    base_url = "https://gmail.googleapis.com/gmail/v1"
    
    with httpx.Client() as client:
        # Get the original message
        msg_response = client.get(
            f"{base_url}/users/me/messages/{message_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": "full"}
        )
        
        if msg_response.status_code != 200:
            return f"Error: Could not retrieve original message. Status: {msg_response.status_code}"
        
        original_msg = msg_response.json()
        headers = {h['name']: h['value'] for h in original_msg.get('payload', {}).get('headers', [])}
        
        # Get original body
        payload = original_msg.get('payload', {})
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    body_data = part.get('body', {}).get('data', '')
                    if body_data:
                        import base64
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                        break
        else:
            body_data = payload.get('body', {}).get('data', '')
            if body_data:
                import base64
                body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
        
        # Build forwarded message
        original_from = headers.get('From', 'Unknown')
        original_date = headers.get('Date', '')
        original_subject = headers.get('Subject', 'No Subject')
        original_to = headers.get('To', '')
        
        forward_header = f"\n\n---------- Forwarded message ---------\n"
        forward_header += f"From: {original_from}\n"
        forward_header += f"Date: {original_date}\n"
        forward_header += f"Subject: {original_subject}\n"
        forward_header += f"To: {original_to}\n\n"
        
        new_body = (comment + forward_header if comment else forward_header) + body
        new_subject = f"Fwd: {original_subject}" if not original_subject.startswith('Fwd:') else original_subject
        
        # Create the new message
        from email.message import EmailMessage
        import base64
        
        message = EmailMessage()
        message.set_content(new_body)
        message["To"] = ", ".join(to_recipients)
        message["Subject"] = new_subject
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send the message
        send_response = client.post(
            f"{base_url}/users/me/messages/send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={"raw": encoded_message}
        )
        
        if send_response.status_code == 200:
            recipients_str = ", ".join(to_recipients)
            return f"Email successfully forwarded to: {recipients_str}"
        else:
            return f"Error: Failed to forward email. Status: {send_response.status_code}. Details: {send_response.text}"


def _reply_gmail_email(
    access_token: str,
    message_id: str,
    comment: str,
    reply_all: bool = False,
    additional_recipients: Optional[List[str]] = None
) -> str:
    """
    Reply to an email using Gmail API.
    
    Gmail doesn't have a native reply endpoint, so we:
    1. Get the original message
    2. Create a reply message with proper headers (In-Reply-To, References, threadId)
    3. Send the reply
    """
    base_url = "https://gmail.googleapis.com/gmail/v1"
    
    with httpx.Client() as client:
        # Get the original message
        msg_response = client.get(
            f"{base_url}/users/me/messages/{message_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": "full"}
        )
        
        if msg_response.status_code != 200:
            return f"Error: Could not retrieve original message. Status: {msg_response.status_code}"
        
        original_msg = msg_response.json()
        thread_id = original_msg.get('threadId', '')
        headers = {h['name']: h['value'] for h in original_msg.get('payload', {}).get('headers', [])}
        
        # Get message ID for threading
        original_message_id = headers.get('Message-ID', headers.get('Message-Id', ''))
        references = headers.get('References', '')
        
        # Determine recipients
        original_from = headers.get('From', '')
        original_to = headers.get('To', '')
        original_cc = headers.get('Cc', '')
        original_subject = headers.get('Subject', 'No Subject')
        
        # For reply, send to the original sender
        # For reply all, include original To and Cc
        if reply_all:
            to_list = [original_from]
            if original_to:
                to_list.extend([addr.strip() for addr in original_to.split(',')])
            if original_cc:
                to_list.extend([addr.strip() for addr in original_cc.split(',')])
        else:
            to_list = [original_from]
        
        # Add additional recipients if provided
        if additional_recipients:
            to_list.extend(additional_recipients)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_to = []
        for addr in to_list:
            addr_lower = addr.lower().strip()
            if addr_lower and addr_lower not in seen:
                seen.add(addr_lower)
                unique_to.append(addr.strip())
        
        # Build reply subject
        reply_subject = f"Re: {original_subject}" if not original_subject.startswith('Re:') else original_subject
        
        # Create the reply message
        from email.message import EmailMessage
        import base64
        
        message = EmailMessage()
        message.set_content(comment)
        message["To"] = ", ".join(unique_to)
        message["Subject"] = reply_subject
        
        # Add threading headers
        if original_message_id:
            message["In-Reply-To"] = original_message_id
            if references:
                message["References"] = f"{references} {original_message_id}"
            else:
                message["References"] = original_message_id
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send the reply in the same thread
        send_response = client.post(
            f"{base_url}/users/me/messages/send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "raw": encoded_message,
                "threadId": thread_id
            }
        )
        
        if send_response.status_code == 200:
            reply_type = "all recipients" if reply_all else "sender"
            return f"Reply successfully sent to {reply_type}."
        else:
            return f"Error: Failed to send reply. Status: {send_response.status_code}. Details: {send_response.text}"


def _delete_gmail_emails(access_token: str, message_ids: List[str]) -> str:
    """
    Move emails to trash in Gmail.
    
    Uses the messages.trash API endpoint to move messages to trash.
    """
    base_url = "https://gmail.googleapis.com/gmail/v1"
    
    if not message_ids:
        return "Error: No message IDs provided."
    
    # Validate message IDs
    valid_ids = [mid.strip() for mid in message_ids if mid and isinstance(mid, str) and len(mid.strip()) > 0]
    
    if not valid_ids:
        return "Error: No valid message IDs provided. Message IDs must be non-empty strings."
    
    trashed_count = 0
    failed_ids = []
    
    with httpx.Client() as client:
        for msg_id in valid_ids:
            response = client.post(
                f"{base_url}/users/me/messages/{msg_id}/trash",
                headers={
                    "Authorization": f"Bearer {access_token}"
                }
            )
            
            if response.status_code == 200:
                trashed_count += 1
            else:
                failed_ids.append(msg_id)
    
    if trashed_count == len(valid_ids):
        return f"Successfully moved {trashed_count} email(s) to trash."
    elif trashed_count > 0:
        return f"Partially successful: Moved {trashed_count} email(s) to trash. Failed to trash {len(failed_ids)} email(s) with IDs: {', '.join(failed_ids[:5])}{'...' if len(failed_ids) > 5 else ''}"
    else:
        return f"Error: Failed to trash any emails. The message IDs may be invalid or already deleted."


def _delete_microsoft_emails(access_token: str, message_ids: List[str]) -> str:
    """
    Delete emails from Microsoft using Graph API.
    
    Microsoft doesn't have batch delete, so we delete one by one.
    """
    base_url = "https://graph.microsoft.com/v1.0"
    
    if not message_ids:
        return "Error: No message IDs provided."
    
    # Validate message IDs
    valid_ids = [mid.strip() for mid in message_ids if mid and isinstance(mid, str) and len(mid.strip()) > 0]
    
    if not valid_ids:
        return "Error: No valid message IDs provided. Message IDs must be non-empty strings."
    
    deleted_count = 0
    failed_ids = []
    
    with httpx.Client() as client:
        for msg_id in valid_ids:
            response = client.delete(
                f"{base_url}/me/messages/{msg_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 204:
                deleted_count += 1
            else:
                failed_ids.append(msg_id)
    
    if deleted_count == len(valid_ids):
        return f"Successfully deleted {deleted_count} email(s)."
    elif deleted_count > 0:
        return f"Partially successful: Deleted {deleted_count} email(s). Failed to delete {len(failed_ids)} email(s) with IDs: {', '.join(failed_ids[:5])}{'...' if len(failed_ids) > 5 else ''}"
    else:
        return f"Error: Failed to delete any emails. The message IDs may be invalid or already deleted."


def _get_gmail_thread(access_token: str, thread_id: str, format: str = "full") -> str:
    """
    Retrieve all messages in a Gmail thread.
    
    Uses the threads.get API endpoint which returns all messages in a conversation.
    """
    base_url = "https://gmail.googleapis.com/gmail/v1"
    
    # Validate thread_id format - Gmail thread IDs are hexadecimal strings
    if not thread_id or not isinstance(thread_id, str):
        return "Error: thread_id is required and must be a non-empty string."
    
    # Remove any whitespace
    thread_id = thread_id.strip()
    
    # Gmail thread IDs are typically 16-character hexadecimal strings
    # But can vary, so we just check for basic validity
    if len(thread_id) < 10:
        return f"Error: Invalid thread_id format '{thread_id}'. Thread IDs should be obtained from email search results or message data."
    
    # Validate format
    valid_formats = ["full", "metadata", "minimal"]
    if format not in valid_formats:
        format = "full"
    
    with httpx.Client() as client:
        response = client.get(
            f"{base_url}/users/me/threads/{thread_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": format}
        )
        
        if response.status_code == 404:
            return f"Error: Thread not found with ID '{thread_id}'. The thread may have been deleted or the ID is incorrect."
        
        if response.status_code == 400:
            return f"Error: Invalid thread ID '{thread_id}'. Please use a valid thread ID from email search results or message data. Thread IDs look like '18abc123def456gh'."
        
        if response.status_code != 200:
            return f"Error: Failed to retrieve thread. Status: {response.status_code}. Please verify the thread_id is correct."
        
        thread_data = response.json()
        
        thread_id = thread_data.get('id', '')
        snippet = thread_data.get('snippet', '')
        messages = thread_data.get('messages', [])
        
        if not messages:
            return f"Thread {thread_id} contains no messages."
        
        # Parse all messages in the thread
        emails_data = []
        for msg in messages:
            if format == "minimal":
                # Minimal format only has id and labels
                emails_data.append({
                    'id': msg.get('id', ''),
                    'labels': ', '.join(msg.get('labelIds', [])),
                    'from': '',
                    'subject': '',
                    'date': '',
                    'to': '',
                    'cc': '',
                    'body': ''
                })
            else:
                # Full or metadata format
                parsed = _parse_gmail_message(msg)
                parsed['id'] = msg.get('id', '')
                parsed['labels'] = ', '.join(msg.get('labelIds', []))
                emails_data.append(parsed)
        
        # Format output
        result = f"Thread ID: {thread_id}\n"
        result += f"Snippet: {snippet}\n"
        result += f"Total messages in thread: {len(messages)}\n\n"
        
        for idx, email_data in enumerate(emails_data, 1):
            result += f"--- Message {idx} of {len(emails_data)} ---\n"
            if email_data.get('id'):
                result += f"Message ID: {email_data.get('id')}\n"
            if email_data.get('labels'):
                result += f"Labels: {email_data.get('labels')}\n"
            if email_data.get('from'):
                result += f"From: {email_data.get('from')}\n"
            if email_data.get('to'):
                result += f"To: {email_data.get('to')}\n"
            if email_data.get('cc'):
                result += f"CC: {email_data.get('cc')}\n"
            if email_data.get('subject'):
                result += f"Subject: {email_data.get('subject')}\n"
            if email_data.get('date'):
                result += f"Date: {email_data.get('date')}\n"
            if email_data.get('body'):
                result += f"Body:\n{email_data.get('body')}\n"
            result += "\n"
        
        return result


def _get_microsoft_conversation(access_token: str, conversation_id: str, group_id: Optional[str] = None) -> str:
    """
    Retrieve all messages in a Microsoft conversation.
    
    For personal mailbox: Uses conversationId to filter messages.
    For Groups: Uses the Group threads API to get thread and its posts.
    
    Args:
        access_token: OAuth access token
        conversation_id: The conversationId (for mailbox) or thread ID (for groups)
        group_id: Optional group ID. If provided, uses Group threads API.
    """
    base_url = "https://graph.microsoft.com/v1.0"
    
    with httpx.Client() as client:
        if group_id:
            # Use Group Threads API for group conversations
            return _get_microsoft_group_thread(client, access_token, base_url, group_id, conversation_id)
        else:
            # Use mailbox messages filtered by conversationId for personal emails
            return _get_microsoft_mailbox_conversation(client, access_token, base_url, conversation_id)


def _get_microsoft_group_thread(client: httpx.Client, access_token: str, base_url: str, group_id: str, thread_id: str) -> str:
    """
    Retrieve a conversation thread from a Microsoft 365 Group.
    
    Uses: GET /groups/{id}/threads/{id}
    """
    # First get the thread metadata
    thread_response = client.get(
        f"{base_url}/groups/{group_id}/threads/{thread_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    if thread_response.status_code == 404:
        return f"Thread not found: {thread_id} in group {group_id}"
    
    if thread_response.status_code != 200:
        raise Exception(f"Failed to retrieve group thread: {thread_response.text}")
    
    thread_data = thread_response.json()
    
    # Get the posts in this thread
    posts_response = client.get(
        f"{base_url}/groups/{group_id}/threads/{thread_id}/posts",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "$select": "from,body,receivedDateTime,hasAttachments,sender",
            "$orderby": "receivedDateTime ASC"
        }
    )
    
    posts = []
    if posts_response.status_code == 200:
        posts = posts_response.json().get('value', [])
    
    # Format output
    result = f"Group Thread ID: {thread_data.get('id', '')}\n"
    result += f"Topic: {thread_data.get('topic', 'No Topic')}\n"
    result += f"Preview: {thread_data.get('preview', '')}\n"
    result += f"Has Attachments: {thread_data.get('hasAttachments', False)}\n"
    result += f"Last Delivered: {thread_data.get('lastDeliveredDateTime', '')}\n"
    result += f"Unique Senders: {', '.join(thread_data.get('uniqueSenders', []))}\n"
    result += f"Is Locked: {thread_data.get('isLocked', False)}\n"
    result += f"Total posts: {len(posts)}\n\n"
    
    for idx, post in enumerate(posts, 1):
        # Extract sender info
        sender_info = post.get('from', {}).get('emailAddress', {})
        sender = sender_info.get('address', post.get('sender', {}).get('emailAddress', {}).get('address', 'Unknown'))
        sender_name = sender_info.get('name', '')
        
        # Get body content
        body_content = post.get('body', {})
        body_text = body_content.get('content', '')[:1000]
        
        result += f"--- Post {idx} of {len(posts)} ---\n"
        result += f"From: {sender_name} <{sender}>\n" if sender_name else f"From: {sender}\n"
        result += f"Date: {post.get('receivedDateTime', '')}\n"
        result += f"Has Attachments: {post.get('hasAttachments', False)}\n"
        result += f"Body:\n{body_text}\n\n"
    
    return result


def _get_microsoft_mailbox_conversation(client: httpx.Client, access_token: str, base_url: str, conversation_id: str) -> str:
    """
    Retrieve all messages in a personal mailbox conversation.
    
    Uses: GET /me/messages?$filter=conversationId eq '...'
    """
    # Filter messages by conversationId
    response = client.get(
        f"{base_url}/me/messages",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "$filter": f"conversationId eq '{conversation_id}'",
            "$select": "from,subject,bodyPreview,receivedDateTime,toRecipients,ccRecipients,body,conversationId",
            "$orderby": "receivedDateTime ASC",  # Chronological order
            "$top": 50  # Get up to 50 messages in conversation
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve conversation: {response.text}")
    
    messages = response.json().get('value', [])
    
    if not messages:
        return f"No messages found in conversation: {conversation_id}"
    
    # Format output
    result = f"Conversation ID: {conversation_id}\n"
    result += f"Total messages in conversation: {len(messages)}\n\n"
    
    for idx, msg in enumerate(messages, 1):
        body_content = msg.get('body', {})
        body_text = body_content.get('content', msg.get('bodyPreview', ''))
        
        if body_content.get('contentType') == 'HTML':
            body_text = msg.get('bodyPreview', body_text)
        
        result += f"--- Message {idx} of {len(messages)} ---\n"
        result += f"From: {msg.get('from', {}).get('emailAddress', {}).get('address', 'Unknown')}\n"
        result += f"To: {', '.join([r.get('emailAddress', {}).get('address', '') for r in msg.get('toRecipients', [])])}\n"
        
        cc_recipients = msg.get('ccRecipients', [])
        if cc_recipients:
            result += f"CC: {', '.join([r.get('emailAddress', {}).get('address', '') for r in cc_recipients])}\n"
        
        result += f"Subject: {msg.get('subject', 'No Subject')}\n"
        result += f"Date: {msg.get('receivedDateTime', '')}\n"
        result += f"Body:\n{body_text[:1000]}\n\n"
    
    return result


def _build_gmail_query(
    query: Optional[str] = None,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    after_date: Optional[str] = None,
    before_date: Optional[str] = None
) -> str:
    """Build a Gmail search query string."""
    parts = []
    
    # Add raw query if provided
    if query:
        parts.append(query)
    
    # Add sender filter
    if sender:
        parts.append(f"from:{sender}")
    
    # Add subject filter
    if subject:
        parts.append(f"subject:{subject}")
    
    # Add keyword filters
    if keywords:
        for keyword in keywords:
            parts.append(keyword)
    
    # Add date filters (Gmail uses YYYY/MM/DD format)
    if after_date:
        # Convert YYYY-MM-DD to YYYY/MM/DD if needed
        formatted_date = after_date.replace('-', '/')
        parts.append(f"after:{formatted_date}")
    
    if before_date:
        formatted_date = before_date.replace('-', '/')
        parts.append(f"before:{formatted_date}")
    
    return ' '.join(parts)


def _search_gmail_emails(
    access_token: str,
    query: Optional[str] = None,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    after_date: Optional[str] = None,
    before_date: Optional[str] = None,
    label_ids: Optional[List[str]] = None,
    include_spam_trash: bool = False,
    max_results: int = 10
) -> str:
    """Search emails using Gmail API."""
    base_url = "https://gmail.googleapis.com/gmail/v1"
    
    # Build the query string
    search_query = _build_gmail_query(
        query=query,
        sender=sender,
        subject=subject,
        keywords=keywords,
        after_date=after_date,
        before_date=before_date
    )
    
    params = {
        "maxResults": max_results,
        "includeSpamTrash": include_spam_trash
    }
    
    if search_query:
        params["q"] = search_query
    
    if label_ids:
        params["labelIds"] = label_ids
    
    with httpx.Client() as client:
        # Search for messages
        list_response = client.get(
            f"{base_url}/users/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params
        )
        
        if list_response.status_code != 200:
            raise Exception(f"Failed to search emails: {list_response.text}")
        
        messages = list_response.json().get('messages', [])
        result_estimate = list_response.json().get('resultSizeEstimate', 0)
        
        if not messages:
            return f"No emails found matching the search criteria. Query: {search_query or 'none'}"
        
        emails_data = []
        
        # Fetch each message
        for msg in messages[:max_results]:
            msg_response = client.get(
                f"{base_url}/users/me/messages/{msg['id']}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "full"}
            )
            
            if msg_response.status_code == 200:
                email_data = msg_response.json()
                emails_data.append(_parse_gmail_message(email_data))
        
        result = _format_emails_for_llm(emails_data)
        result = f"Search query: {search_query or 'none'}\nEstimated total results: {result_estimate}\n\n{result}"
        return result


def _build_microsoft_search_query(
    query: Optional[str] = None,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    after_date: Optional[str] = None,
    before_date: Optional[str] = None
) -> str:
    """Build a Microsoft Search query string using KQL (Keyword Query Language)."""
    parts = []
    
    # Add raw query if provided
    if query:
        parts.append(query)
    
    # Add sender filter
    if sender:
        parts.append(f"from:{sender}")
    
    # Add subject filter
    if subject:
        parts.append(f"subject:{subject}")
    
    # Add keyword filters
    if keywords:
        for keyword in keywords:
            parts.append(keyword)
    
    # Add date filters (Microsoft uses received:>=YYYY-MM-DD format)
    if after_date:
        formatted_date = after_date.replace('/', '-')
        parts.append(f"received>={formatted_date}")
    
    if before_date:
        formatted_date = before_date.replace('/', '-')
        parts.append(f"received<{formatted_date}")
    
    return ' '.join(parts) if parts else '*'


def _search_microsoft_emails(
    access_token: str,
    query: Optional[str] = None,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    after_date: Optional[str] = None,
    before_date: Optional[str] = None,
    max_results: int = 10
) -> str:
    """Search emails using Microsoft Graph Search API.
    
    Uses the /search/query endpoint which provides:
    - Full-text search across body and attachments
    - Relevance ranking
    - KQL (Keyword Query Language) support
    """
    base_url = "https://graph.microsoft.com/v1.0"
    
    # Build the search query string using KQL
    search_query = _build_microsoft_search_query(
        query=query,
        sender=sender,
        subject=subject,
        keywords=keywords,
        after_date=after_date,
        before_date=before_date
    )
    
    # Build the search request body
    search_request = {
        "requests": [
            {
                "entityTypes": ["message"],
                "query": {
                    "queryString": search_query
                },
                "from": 0,
                "size": min(max_results, 25),  # Microsoft Search API max is 25 per request
                "enableTopResults": True  # Sort by relevance
            }
        ]
    }
    
    with httpx.Client() as client:
        response = client.post(
            f"{base_url}/search/query",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=search_request
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to search emails: {response.text}")
        
        result = response.json()
        
        # Parse the search response
        hits_containers = result.get('value', [{}])[0].get('hitsContainers', [])
        
        if not hits_containers:
            return f"No emails found matching the search criteria. Query: {search_query}"
        
        hits_container = hits_containers[0]
        total = hits_container.get('total', 0)
        more_available = hits_container.get('moreResultsAvailable', False)
        hits = hits_container.get('hits', [])
        
        if not hits:
            return f"No emails found matching the search criteria. Query: {search_query}"
        
        emails_data = []
        for hit in hits:
            resource = hit.get('resource', {})
            summary = hit.get('summary', '')
            
            # Extract sender info
            sender_info = resource.get('sender', {}).get('emailAddress', {})
            from_info = resource.get('from', {}).get('emailAddress', {})
            sender_address = from_info.get('address') or sender_info.get('address', 'Unknown')
            sender_name = from_info.get('name') or sender_info.get('name', '')
            
            # Use bodyPreview or summary
            body_text = resource.get('bodyPreview', summary)[:1000]
            
            emails_data.append({
                'from': f"{sender_name} <{sender_address}>" if sender_name else sender_address,
                'subject': resource.get('subject', 'No Subject'),
                'date': resource.get('receivedDateTime', ''),
                'to': '',  # Not included in search results by default
                'cc': '',
                'body': body_text,
                'rank': hit.get('rank', 0),
                'has_attachments': resource.get('hasAttachments', False)
            })
        
        result_str = _format_emails_for_llm(emails_data)
        result_str = f"Search query: {search_query}\nTotal results: {total}\nMore results available: {more_available}\n\n{result_str}"
        return result_str


def _search_imap_emails(
    host: str,
    port: int,
    username: str,
    password: str,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    after_date: Optional[str] = None,
    before_date: Optional[str] = None,
    max_results: int = 10
) -> str:
    """Search emails using IMAP."""
    import imaplib
    import email
    from email.header import decode_header
    from datetime import datetime
    
    try:
        imap = imaplib.IMAP4_SSL(host, port)
        imap.login(username, password)
        imap.select('INBOX')
        
        # Build IMAP search criteria
        criteria = []
        
        if sender:
            criteria.append(f'FROM "{sender}"')
        
        if subject:
            criteria.append(f'SUBJECT "{subject}"')
        
        if keywords:
            for kw in keywords:
                criteria.append(f'BODY "{kw}"')
        
        if after_date:
            # Convert YYYY/MM/DD or YYYY-MM-DD to DD-Mon-YYYY
            date_str = after_date.replace('/', '-')
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            imap_date = dt.strftime('%d-%b-%Y')
            criteria.append(f'SINCE {imap_date}')
        
        if before_date:
            date_str = before_date.replace('/', '-')
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            imap_date = dt.strftime('%d-%b-%Y')
            criteria.append(f'BEFORE {imap_date}')
        
        # Default to ALL if no criteria
        search_string = ' '.join(criteria) if criteria else 'ALL'
        
        _, message_numbers = imap.search(None, search_string)
        
        if not message_numbers[0]:
            imap.logout()
            return "No emails found matching the search criteria."
        
        email_ids = message_numbers[0].split()
        email_ids = email_ids[-max_results:] if len(email_ids) > max_results else email_ids
        email_ids.reverse()
        
        emails_data = []
        
        for email_id in email_ids:
            _, msg_data = imap.fetch(email_id, '(RFC822)')
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            subj = email_message.get('Subject', 'No Subject')
            if subj:
                decoded_subject = decode_header(subj)
                subj = decoded_subject[0][0]
                if isinstance(subj, bytes):
                    subj = subj.decode(decoded_subject[0][1] or 'utf-8')
            
            body = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode()
                            break
                        except:
                            pass
            else:
                try:
                    body = email_message.get_payload(decode=True).decode()
                except:
                    body = str(email_message.get_payload())
            
            emails_data.append({
                'from': email_message.get('From', 'Unknown'),
                'subject': subj,
                'date': email_message.get('Date', ''),
                'to': email_message.get('To', ''),
                'cc': email_message.get('Cc', ''),
                'body': body[:1000]
            })
        
        imap.logout()
        return _format_emails_for_llm(emails_data)
        
    except Exception as e:
        raise Exception(f"Failed to search IMAP emails: {str(e)}")


def _retrieve_gmail_emails(access_token: str, n: int) -> str:
    """Retrieve emails from Gmail API."""
    base_url = "https://gmail.googleapis.com/gmail/v1"
    
    with httpx.Client() as client:
        # Get list of message IDs from INBOX
        list_response = client.get(
            f"{base_url}/users/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "maxResults": min(n, 20),  # Limit to 20 emails
                "labelIds": ["INBOX"]
            }
        )
        
        if list_response.status_code != 200:
            raise Exception(f"Failed to list emails: {list_response.text}")
        
        messages = list_response.json().get('messages', [])
        
        if not messages:
            return "No emails found."
        
        emails_data = []
        
        # Fetch each message with format=full to get complete content
        for msg in messages[:n]:
            msg_response = client.get(
                f"{base_url}/users/me/messages/{msg['id']}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "full"}
            )
            
            if msg_response.status_code == 200:
                email_data = msg_response.json()
                emails_data.append(_parse_gmail_message(email_data))
        
        return _format_emails_for_llm(emails_data)


def _retrieve_microsoft_emails(access_token: str, n: int) -> str:
    """Retrieve emails from Microsoft Graph API."""
    base_url = "https://graph.microsoft.com/v1.0"
    
    with httpx.Client() as client:
        response = client.get(
            f"{base_url}/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "$top": min(n, 20),  # Limit to 20 emails
                "$select": "from,subject,bodyPreview,receivedDateTime,toRecipients,ccRecipients,body",
                "$orderby": "receivedDateTime DESC"  # Most recent first
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve emails: {response.text}")
        
        messages = response.json().get('value', [])
        
        if not messages:
            return "No emails found."
        
        emails_data = []
        for msg in messages:
            # Get body content - prefer text over HTML
            body_content = msg.get('body', {})
            body_text = body_content.get('content', msg.get('bodyPreview', ''))
            
            # If HTML body, try to use bodyPreview which is plain text
            if body_content.get('contentType') == 'HTML':
                body_text = msg.get('bodyPreview', body_text)
            
            emails_data.append({
                'from': msg.get('from', {}).get('emailAddress', {}).get('address', 'Unknown'),
                'subject': msg.get('subject', 'No Subject'),
                'date': msg.get('receivedDateTime', ''),
                'to': ', '.join([r.get('emailAddress', {}).get('address', '') for r in msg.get('toRecipients', [])]),
                'cc': ', '.join([r.get('emailAddress', {}).get('address', '') for r in msg.get('ccRecipients', [])]),
                'body': body_text[:1000]  # Limit body length
            })
        
        return _format_emails_for_llm(emails_data)


def _retrieve_imap_emails(host: str, port: int, username: str, password: str, n: int) -> str:
    """Retrieve emails from IMAP server."""
    import imaplib
    import email
    from email.header import decode_header
    
    try:
        # Connect to IMAP server
        imap = imaplib.IMAP4_SSL(host, port)
        imap.login(username, password)
        imap.select('INBOX')
        
        # Search for all emails
        _, message_numbers = imap.search(None, 'ALL')
        
        if not message_numbers[0]:
            imap.logout()
            return "No emails found."
        
        # Get the last N email IDs (max 20)
        email_ids = message_numbers[0].split()
        max_emails = min(n, 20)
        email_ids = email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids
        email_ids.reverse()  # Most recent first
        
        emails_data = []
        
        for email_id in email_ids:
            _, msg_data = imap.fetch(email_id, '(RFC822)')
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Decode subject
            subject = email_message.get('Subject', 'No Subject')
            if subject:
                decoded_subject = decode_header(subject)
                subject = decoded_subject[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode(decoded_subject[0][1] or 'utf-8')
            
            # Get body
            body = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode()
                            break
                        except:
                            pass
            else:
                try:
                    body = email_message.get_payload(decode=True).decode()
                except:
                    body = str(email_message.get_payload())
            
            emails_data.append({
                'from': email_message.get('From', 'Unknown'),
                'subject': subject,
                'date': email_message.get('Date', ''),
                'to': email_message.get('To', ''),
                'cc': email_message.get('Cc', ''),
                'body': body[:1000]  # Limit body length
            })
        
        imap.logout()
        return _format_emails_for_llm(emails_data)
        
    except Exception as e:
        raise Exception(f"Failed to retrieve IMAP emails: {str(e)}")


def _parse_gmail_message(message_data: dict) -> dict:
    """Parse Gmail API message format."""
    headers = {h['name']: h['value'] for h in message_data.get('payload', {}).get('headers', [])}
    
    # Get body
    body = ""
    payload = message_data.get('payload', {})
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain':
                body_data = part.get('body', {}).get('data', '')
                if body_data:
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                    break
    else:
        body_data = payload.get('body', {}).get('data', '')
        if body_data:
            body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
    
    return {
        'message_id': message_data.get('id', ''),
        'thread_id': message_data.get('threadId', ''),
        'from': headers.get('From', 'Unknown'),
        'subject': headers.get('Subject', 'No Subject'),
        'date': headers.get('Date', ''),
        'to': headers.get('To', ''),
        'cc': headers.get('Cc', ''),
        'body': body[:1000]  # Limit body length
    }


def _format_emails_for_llm(emails: List[dict]) -> str:
    """Format emails as a string for LLM processing."""
    formatted = f"Retrieved {len(emails)} email(s):\n\n"
    
    for idx, email in enumerate(emails, 1):
        formatted += f"--- Email {idx} ---\n"
        if email.get('message_id'):
            formatted += f"Message ID: {email.get('message_id')}\n"
        if email.get('thread_id'):
            formatted += f"Thread ID: {email.get('thread_id')} (use this with get_thread_messages to see full conversation)\n"
        formatted += f"From: {email.get('from', 'Unknown')}\n"
        formatted += f"To: {email.get('to', '')}\n"
        if email.get('cc'):
            formatted += f"CC: {email.get('cc')}\n"
        formatted += f"Subject: {email.get('subject', 'No Subject')}\n"
        formatted += f"Date: {email.get('date', '')}\n"
        formatted += f"Body:\n{email.get('body', '')}\n"
        formatted += "\n"
    
    return formatted
