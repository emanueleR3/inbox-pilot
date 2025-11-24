import smtplib
import base64
import mimetypes
import os
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
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
                if cc_recipients:
                    msg['Cc'] = ', '.join(cc_recipients)
                return msg
        
        msg['Subject'] = subject
        msg['From'] = sender_address
        msg['To'] = receiver_address
        
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
        print(f"\n\nemail_service.py - send_email() - parameters:\nsender_address: {sender_address}\nreceiver_address: {receiver_address}\nsubject: {subject}\nbody: {body}\nbody_type: {body_type}\ncc_recipients: {cc_recipients}\nbcc_recipients: {bcc_recipients}\nattachments: {attachments}\n")
        msg = self._create_message(
            sender_address, receiver_address, subject, body,
            body_type, cc_recipients, bcc_recipients, attachments
        )
        
        all_recipients = [receiver_address]
        if cc_recipients:
            all_recipients.extend(cc_recipients)
        if bcc_recipients:
            all_recipients.extend(bcc_recipients)
        
        with smtplib.SMTP(self.host, self.port) as server:
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
        formatted += f"From: {email.get('from', 'Unknown')}\n"
        formatted += f"To: {email.get('to', '')}\n"
        if email.get('cc'):
            formatted += f"CC: {email.get('cc')}\n"
        formatted += f"Subject: {email.get('subject', 'No Subject')}\n"
        formatted += f"Date: {email.get('date', '')}\n"
        formatted += f"Body:\n{email.get('body', '')}\n"
        formatted += "\n"
    
    return formatted
