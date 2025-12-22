"""
Email sending service for Gmail, Microsoft, and SMTP providers.
Handles authentication, token decryption, and email sending logic.
"""

import os
import logging
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import make_msgid
from typing import Optional, List, Dict
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import requests
import ssl

from ..utils.utils import decrypt

load_dotenv()

logger = logging.getLogger(__name__)


def _clean_message_id(message_id: str) -> str:
    """
    Remove angle brackets from message ID if present.
    Example: "<abc123@mail.gmail.com>" -> "abc123@mail.gmail.com"
    """
    if not message_id:
        return message_id
    
    if message_id.startswith('<') and message_id.endswith('>'):
        return message_id[1:-1]
    
    return message_id


class SendEmailService:
    """Service for sending emails via Gmail, Microsoft, and SMTP."""
    
    def __init__(self):
        """Initialize the email service."""
        pass

    
    def send_email_gmail(
        self, 
        email: str, 
        subject: str, 
        body: str, 
        hashed_access_token: str,
        thread_id: Optional[str] = None,
        message_id: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> dict:
        """
        Send email via Gmail API.
        
        Args:
            email: Recipient email
            subject: Email subject
            body: Email body (HTML or plain text)
            hashed_access_token: Encrypted access token
            thread_id: Optional Gmail thread ID for replies
            message_id: Optional RFC message ID for In-Reply-To header
            attachments: Optional list of attachments, each dict with:
                - filename: str (e.g., "invite.ics")
                - content: str (base64 encoded content)
                - content_type: str (e.g., "text/calendar")
        """
        try:

            # Decrypt the access token
            access_token = decrypt(hashed_access_token, "token")

            if not access_token:
                raise ValueError("Failed to decrypt access token")

            scopes_env = os.getenv("GOOGLE_SCOPES", "")

            if scopes_env:
                scopes = [scope.strip() for scope in scopes_env.split() if scope.strip()]
            else:
                scopes = [
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.modify",
                ]

            creds = Credentials(
                token=access_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                scopes=scopes
            )

            service = build('gmail', 'v1', credentials=creds)

            # Create email - use 'mixed' for attachments, 'alternative' for body variants
            if attachments:
                # When we have attachments, use mixed as the outer container
                message = MIMEMultipart('mixed')
            else:
                # No attachments, use alternative for body
                message = MIMEMultipart('alternative')
                
            message['To'] = email
            message['Subject'] = subject

            if message_id:
                # Ensure message_id has angle brackets for RFC compliance
                rfc_message_id = message_id if message_id.startswith('<') else f"<{message_id}>"
                message['In-Reply-To'] = rfc_message_id
                message['References'] = rfc_message_id

            # Detect body type and create body part
            if body.strip().startswith("<") and body.strip().endswith(">"):
                body_part = MIMEText(body, 'html', 'utf-8')
            else:
                body_part = MIMEText(body, 'plain', 'utf-8')

            if attachments:
                # For mixed messages, wrap body in alternative container
                body_container = MIMEMultipart('alternative')
                body_container.attach(body_part)
                message.attach(body_container)
            else:
                message.attach(body_part)

            # Handle attachments
            if attachments:
                for attachment in attachments:
                    filename = attachment.get('filename', 'attachment')
                    content_b64 = attachment.get('content', '')
                    content_type = attachment.get('content_type', 'application/octet-stream')
                    
                    try:
                        # Decode base64 content
                        content_bytes = base64.b64decode(content_b64)
                        
                        # For ICS files, use application/ics for better Gmail compatibility
                        if filename.endswith('.ics') and content_type == 'text/calendar':
                            content_type = 'application/ics'
                        
                        # Create attachment part
                        maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')
                        att_part = MIMEBase(maintype, subtype)
                        att_part.set_payload(content_bytes)
                        encoders.encode_base64(att_part)
                        
                        # Add headers to ensure attachment is visible
                        att_part.add_header('Content-Disposition', 'attachment', filename=filename)
                        att_part.add_header('Content-Transfer-Encoding', 'base64')
                        
                        message.attach(att_part)
                        print(f"   📎 Attached: {filename} ({content_type})")
                    except Exception as att_err:
                        print(f"   ⚠️ Failed to attach {filename}: {att_err}")

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            message_body = {"raw": raw_message}

            if thread_id:
                message_body["threadId"] = thread_id

            send_result = service.users().messages().send(
                userId='me',
                body=message_body
            ).execute()

            gmail_internal_id = send_result.get("id")

            # Retrieve RFC Message-ID
            rfc_message_id = None

            try:
                msg = service.users().messages().get(
                    userId="me",
                    id=gmail_internal_id,
                    format="metadata",
                    metadataHeaders=["Message-ID", "Message-Id"]
                ).execute()

                for h in msg.get("payload", {}).get("headers", []):
                    print(f"   - {h.get('name')}: {h.get('value')}")
                    if h.get("name", "").lower() == "message-id":
                        rfc_message_id = h.get("value")

            except Exception as err:
                print(f"[DEBUG] Could not fetch RFC Message-ID: {err}")

            print("=== EMAIL SENT SUCCESSFULLY ===\n")

            # Clean message_id by removing angle brackets
            cleaned_message_id = _clean_message_id(rfc_message_id)

            return {
                "success": True,
                "message": f"Email sent to {email}",
                "notification_id": gmail_internal_id,
                "message_id": cleaned_message_id
            }

        except Exception as e:
            print("\n❌ ERROR SENDING EMAIL ❌")
            print(str(e))
            print("==============================\n")

            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}",
                "notification_id": None,
                "message_id": None
            }


    
    def send_email_microsoft(
        self, 
        email: str, 
        subject: str, 
        body: str, 
        hashed_access_token: str,
        message_id: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> dict:
        """
        Send an email using Microsoft Graph API and return RFC Message-ID (internetMessageId).
        
        Args:
            email: Recipient email
            subject: Email subject
            body: Email body (HTML or plain text)
            hashed_access_token: Encrypted access token
            message_id: Optional message ID for reply
            attachments: Optional list of attachments, each dict with:
                - filename: str (e.g., "invite.ics")
                - content: str (base64 encoded content)
                - content_type: str (e.g., "text/calendar")
        """
        try:
            logger.info(f"📤 Sending email via Microsoft Graph to {email}")
        
            # Decrypt the access token
            access_token = decrypt(hashed_access_token, "token")
            if not access_token:
                raise ValueError("Failed to decrypt access token")
        
            # Determine content type
            content_type = "HTML" if body.strip().startswith('<') and body.strip().endswith('>') else "Text"
        
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        
            # 1️⃣ CREA IL MESSAGGIO (DRAFT)
            if message_id:
                # Caso REPLY: usiamo createReply per generare una bozza di risposta
                create_url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/createReply"
                # Per createReply, il corpo va in "comment" se vogliamo aggiungere testo
                # Nota: createReply imposta automaticamente Subject (Re: ...) e To/Cc
                reply_payload = {
                    "comment": body
                }
                create_resp = requests.post(create_url, json=reply_payload, headers=headers)
            else:
                # Caso NUOVA EMAIL
                create_url = "https://graph.microsoft.com/v1.0/me/messages"
                email_message = {
                    "subject": subject,
                    "body": {
                        "contentType": content_type,
                        "content": body
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": email
                            }
                        }
                    ],
                }
                create_resp = requests.post(create_url, json=email_message, headers=headers)

            if create_resp.status_code not in (200, 201):
                error_msg = f"Microsoft Graph create draft error: {create_resp.status_code} - {create_resp.text}"
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "notification_id": None,
                    "message_id": None
                }
        
            created_msg = create_resp.json()
            msg_id = created_msg.get("id")
            logger.info(f"📝 Draft created in Microsoft Graph. ID: {msg_id}")
        
            # 2️⃣ ADD ATTACHMENTS (if any)
            if attachments and msg_id:
                for attachment in attachments:
                    try:
                        filename = attachment.get('filename', 'attachment')
                        content_b64 = attachment.get('content', '')
                        content_type = attachment.get('content_type', 'application/octet-stream')
                        
                        attach_url = f"https://graph.microsoft.com/v1.0/me/messages/{msg_id}/attachments"
                        attach_payload = {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": filename,
                            "contentType": content_type,
                            "contentBytes": content_b64
                        }
                        attach_resp = requests.post(attach_url, json=attach_payload, headers=headers)
                        
                        if attach_resp.status_code in (200, 201):
                            logger.info(f"📎 Attached: {filename} ({content_type})")
                        else:
                            logger.warning(f"⚠️ Failed to attach {filename}: {attach_resp.status_code} - {attach_resp.text}")
                    except Exception as att_err:
                        logger.warning(f"⚠️ Error attaching {filename}: {att_err}")
        
            # 3️⃣ INVIA IL MESSAGGIO
            send_url = f"https://graph.microsoft.com/v1.0/me/messages/{msg_id}/send"
            send_resp = requests.post(send_url, headers=headers)
        
            if send_resp.status_code != 202:
                error_msg = f"Microsoft Graph send error: {send_resp.status_code} - {send_resp.text}"
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "notification_id": msg_id,
                    "message_id": None
                }
        
            logger.info(f"✅ Email sent successfully via Microsoft Graph to {email}")
        
            # 4️⃣ RECUPERA l'RFC Message-ID (internetMessageId)
            rfc_message_id = None
            try:
                get_url = f"https://graph.microsoft.com/v1.0/me/messages/{msg_id}"
                # $select per limitare i dati
                get_resp = requests.get(
                    get_url,
                    headers=headers,
                    params={"$select": "id,internetMessageId"}
                )
                if get_resp.status_code == 200:
                    msg_obj = get_resp.json()
                    rfc_message_id = msg_obj.get("internetMessageId")
                    logger.info(f"📎 Microsoft RFC Message-ID (internetMessageId): {rfc_message_id}")
                else:
                    logger.warning(
                        f"⚠️ Could not retrieve internetMessageId: "
                        f"{get_resp.status_code} - {get_resp.text}"
                    )
            except Exception as meta_err:
                logger.warning(f"⚠️ Error retrieving internetMessageId: {meta_err}", exc_info=True)
        
            # Clean message_id by removing angle brackets
            cleaned_message_id = _clean_message_id(rfc_message_id)

            return {
                "success": True,
                "message": f"Email sent successfully via Microsoft to {email}",
                "notification_id": msg_id,       # id interno Graph del messaggio
                "message_id": cleaned_message_id     # RFC Message-ID (cleaned)
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to send email via Microsoft: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to send email via Microsoft: {str(e)}",
                "notification_id": None,
                "message_id": None
            }

    def send_email_smtp(
        self,
        email: str,
        subject: str,
        body: str,
        smtp_port: int,
        smtp_server: str,
        smtp_email: str,
        password: str,
        reply_to_id: Optional[str] = None,
        message_id: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> dict:
        """
        Send email via SMTP.
        
        Args:
            email: Recipient email
            subject: Email subject
            body: Email body (HTML or plain text)
            smtp_port: SMTP port (465, 587, or 25)
            smtp_server: SMTP server hostname
            smtp_email: Sender email
            password: SMTP password
            reply_to_id: Optional message ID for In-Reply-To header
            message_id: Optional message ID for References header
            attachments: Optional list of attachments, each dict with:
                - filename: str (e.g., "invite.ics")
                - content: str (base64 encoded content)
                - content_type: str (e.g., "text/calendar")
        """
        try:
            print("🔵 [SERVICE] ---- START send_email_smtp ----")

            print(f"🔵 [SERVICE] email={email}")
            print(f"🔵 [SERVICE] subject={subject}")
            print(f"🔵 [SERVICE] body_length={len(body) if body else 0}")
            print(f"🔵 [SERVICE] smtp_port={smtp_port}")
            print(f"🔵 [SERVICE] smtp_server={smtp_server}")
            print(f"🔵 [SERVICE] smtp_email={smtp_email}")
            print(f"🔵 [SERVICE] reply_to_id={reply_to_id}")
            print(f"🔵 [SERVICE] message_id={message_id}")
            print("🔵 [SERVICE] password received (not printed)")

            sender_email = smtp_email

            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = sender_email
            message["To"] = email
            message["Subject"] = subject

            # RFC Message-ID
            msg_id = make_msgid()
            message["Message-ID"] = msg_id
            print(f"🔵 [SERVICE] Generated RFC Message-ID={msg_id}")

            # Reply headers
            if reply_to_id:
                rfc_reply_to_id = reply_to_id if reply_to_id.startswith('<') else f"<{reply_to_id}>"
                message["In-Reply-To"] = rfc_reply_to_id
                print(f"🔵 [SERVICE] In-Reply-To={rfc_reply_to_id}")

            if message_id:
                rfc_message_id = message_id if message_id.startswith('<') else f"<{message_id}>"
                message["References"] = rfc_message_id
                print(f"🔵 [SERVICE] References={rfc_message_id}")

            # Body type
            if body.strip().startswith("<"):
                print("🔵 [SERVICE] Body detected as HTML")
                message.attach(MIMEText(body, "html", "utf-8"))
            else:
                print("🔵 [SERVICE] Body detected as TEXT")
                message.attach(MIMEText(body, "plain", "utf-8"))

            # Handle attachments
            if attachments:
                for attachment in attachments:
                    filename = attachment.get('filename', 'attachment')
                    content_b64 = attachment.get('content', '')
                    content_type = attachment.get('content_type', 'application/octet-stream')
                    
                    try:
                        # Decode base64 content
                        content_bytes = base64.b64decode(content_b64)
                        
                        # Create attachment part
                        maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')
                        att_part = MIMEBase(maintype, subtype)
                        att_part.set_payload(content_bytes)
                        encoders.encode_base64(att_part)
                        att_part.add_header('Content-Disposition', 'attachment', filename=filename)
                        message.attach(att_part)
                        print(f"🔵 [SERVICE] Attached: {filename} ({content_type})")
                    except Exception as att_err:
                        print(f"🟡 [SERVICE] Failed to attach {filename}: {att_err}")

            context = ssl.create_default_context()
            print(f"🔵 [SERVICE] Selecting SMTP flow for port {smtp_port}...")

            # SMTP 465 SSL
            if smtp_port == 465:
                print("🟣 [SERVICE] Connecting with SMTP_SSL...")
                with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                    server.ehlo()
                    print("🟣 [SERVICE] Logging in...")
                    server.login(sender_email, password)
                    print("🟣 [SERVICE] Login OK")
                    server.send_message(message)
                    print("🟣 [SERVICE] Message sent via SSL")

            # SMTP 587 STARTTLS
            elif smtp_port == 587:
                print("🟠 [SERVICE] Connecting with STARTTLS...")
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.ehlo()
                    print("🟠 [SERVICE] Starting TLS...")
                    server.starttls(context=context)
                    server.ehlo()
                    print("🟠 [SERVICE] Logging in...")
                    server.login(sender_email, password)
                    print("🟠 [SERVICE] Login OK")
                    server.send_message(message)
                    print("🟠 [SERVICE] Message sent via STARTTLS")

            # SMTP 25 (optional TLS/login)
            elif smtp_port == 25:
                print("🟢 [SERVICE] Connecting on port 25...")
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.ehlo()

                    try:
                        print("🟢 [SERVICE] Trying STARTTLS...")
                        server.starttls(context=context)
                        server.ehlo()
                        print("🟢 [SERVICE] STARTTLS OK")
                    except Exception as e_tls:
                        print(f"🟡 [SERVICE] STARTTLS not available: {e_tls}")

                    try:
                        print("🟢 [SERVICE] Logging in...")
                        server.login(sender_email, password)
                        print("🟢 [SERVICE] Login OK")
                    except Exception as e_login:
                        print(f"🟡 [SERVICE] Login failed/not required: {e_login}")

                    print("🟢 [SERVICE] Sending message...")
                    server.send_message(message)
                    print("🟢 [SERVICE] Message sent via port 25")

            else:
                print(f"🔴 [SERVICE] Unsupported port: {smtp_port}")
                return {
                    "success": False,
                    "message": f"Unsupported SMTP port {smtp_port}. Use 465 / 587 / 25.",
                    "message_id": None
                }

            cleaned_message_id = _clean_message_id(msg_id)
            print(f"🟩 [SERVICE] Email sent successfully. Cleaned Message-ID={cleaned_message_id}")

            return {
                "success": True,
                "message": "Email sent",
                "message_id": cleaned_message_id,
                "notification_id": cleaned_message_id
            }

        except Exception as e:
            print("🔴 [SERVICE] ERROR sending email!")
            print(f"🔴 [SERVICE] Exception type: {type(e).__name__}")
            print(f"🔴 [SERVICE] Exception message: {str(e)}")
            print(f"🔴 [SERVICE] Exception repr: {repr(e)}")

            return {
                "success": False,
                "message": str(e) or repr(e),
                "message_id": None,
                "notification_id": None
            }

    def create_draft_gmail(
        self, 
        email: str, 
        subject: str, 
        body: str, 
        hashed_access_token: str,
        thread_id: Optional[str] = None,
        message_id: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> dict:
        """
        Create a draft in Gmail instead of sending.
        
        Args:
            email: Recipient email
            subject: Email subject
            body: Email body (HTML or plain text)
            hashed_access_token: Encrypted access token
            thread_id: Optional Gmail thread ID for replies
            message_id: Optional RFC message ID for In-Reply-To header
            attachments: Optional list of attachments
        """
        try:
            logger.info(f"📝 Creating Gmail draft for {email}")
            
            # Decrypt the access token
            access_token = decrypt(hashed_access_token, "token")
            if not access_token:
                raise ValueError("Failed to decrypt access token")

            scopes_env = os.getenv("GOOGLE_SCOPES", "")
            if scopes_env:
                scopes = [scope.strip() for scope in scopes_env.split() if scope.strip()]
            else:
                scopes = [
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.modify",
                ]

            creds = Credentials(
                token=access_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                scopes=scopes
            )

            service = build('gmail', 'v1', credentials=creds)

            # Create email message
            if attachments:
                message = MIMEMultipart('mixed')
            else:
                message = MIMEMultipart('alternative')
                
            message['To'] = email
            message['Subject'] = subject

            if message_id:
                rfc_message_id = message_id if message_id.startswith('<') else f"<{message_id}>"
                message['In-Reply-To'] = rfc_message_id
                message['References'] = rfc_message_id

            # Body
            if body.strip().startswith("<") and body.strip().endswith(">"):
                body_part = MIMEText(body, 'html', 'utf-8')
            else:
                body_part = MIMEText(body, 'plain', 'utf-8')

            if attachments:
                body_container = MIMEMultipart('alternative')
                body_container.attach(body_part)
                message.attach(body_container)
            else:
                message.attach(body_part)

            # Handle attachments
            if attachments:
                for attachment in attachments:
                    filename = attachment.get('filename', 'attachment')
                    content_b64 = attachment.get('content', '')
                    content_type = attachment.get('content_type', 'application/octet-stream')
                    
                    try:
                        content_bytes = base64.b64decode(content_b64)
                        maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')
                        att_part = MIMEBase(maintype, subtype)
                        att_part.set_payload(content_bytes)
                        encoders.encode_base64(att_part)
                        att_part.add_header('Content-Disposition', 'attachment', filename=filename)
                        message.attach(att_part)
                    except Exception as att_err:
                        logger.warning(f"Failed to attach {filename}: {att_err}")

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            draft_body = {"message": {"raw": raw_message}}
            if thread_id:
                draft_body["message"]["threadId"] = thread_id

            # Create draft instead of sending
            draft_result = service.users().drafts().create(
                userId='me',
                body=draft_body
            ).execute()

            draft_id = draft_result.get("id")
            logger.info(f"✅ Gmail draft created successfully. Draft ID: {draft_id}")

            return {
                "success": True,
                "message": f"Draft created for {email}",
                "draft_id": draft_id,
                "notification_id": draft_id
            }

        except Exception as e:
            logger.error(f"❌ Failed to create Gmail draft: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to create draft: {str(e)}",
                "draft_id": None,
                "notification_id": None
            }

    def create_draft_microsoft(
        self, 
        email: str, 
        subject: str, 
        body: str, 
        hashed_access_token: str,
        message_id: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> dict:
        """
        Create a draft in Microsoft Outlook instead of sending.
        Uses Graph API to create message without sending.
        
        Args:
            email: Recipient email
            subject: Email subject
            body: Email body (HTML or plain text)
            hashed_access_token: Encrypted access token
            message_id: Optional message ID for reply
            attachments: Optional list of attachments
        """
        try:
            logger.info(f"📝 Creating Microsoft draft for {email}")
        
            access_token = decrypt(hashed_access_token, "token")
            if not access_token:
                raise ValueError("Failed to decrypt access token")
        
            content_type = "HTML" if body.strip().startswith('<') and body.strip().endswith('>') else "Text"
        
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        
            # Create draft message
            if message_id:
                # Reply case: use createReply but don't send
                create_url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/createReply"
                reply_payload = {"comment": body}
                create_resp = requests.post(create_url, json=reply_payload, headers=headers)
            else:
                # New email case
                create_url = "https://graph.microsoft.com/v1.0/me/messages"
                email_message = {
                    "subject": subject,
                    "body": {
                        "contentType": content_type,
                        "content": body
                    },
                    "toRecipients": [
                        {"emailAddress": {"address": email}}
                    ],
                }
                create_resp = requests.post(create_url, json=email_message, headers=headers)

            if create_resp.status_code not in (200, 201):
                error_msg = f"Microsoft Graph create draft error: {create_resp.status_code} - {create_resp.text}"
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "draft_id": None,
                    "notification_id": None
                }
        
            created_msg = create_resp.json()
            msg_id = created_msg.get("id")
            logger.info(f"📝 Microsoft draft created. ID: {msg_id}")
        
            # Add attachments if any
            if attachments and msg_id:
                for attachment in attachments:
                    try:
                        filename = attachment.get('filename', 'attachment')
                        content_b64 = attachment.get('content', '')
                        content_type = attachment.get('content_type', 'application/octet-stream')
                        
                        attach_url = f"https://graph.microsoft.com/v1.0/me/messages/{msg_id}/attachments"
                        attach_payload = {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": filename,
                            "contentType": content_type,
                            "contentBytes": content_b64
                        }
                        attach_resp = requests.post(attach_url, json=attach_payload, headers=headers)
                        
                        if attach_resp.status_code in (200, 201):
                            logger.info(f"📎 Attached: {filename}")
                        else:
                            logger.warning(f"⚠️ Failed to attach {filename}: {attach_resp.status_code}")
                    except Exception as att_err:
                        logger.warning(f"⚠️ Error attaching {filename}: {att_err}")
        
            # DO NOT SEND - leave as draft
            logger.info(f"✅ Microsoft draft created successfully (not sent)")

            return {
                "success": True,
                "message": f"Draft created for {email}",
                "draft_id": msg_id,
                "notification_id": msg_id
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to create Microsoft draft: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to create draft: {str(e)}",
                "draft_id": None,
                "notification_id": None
            }

    def create_draft_imap(
        self,
        email: str,
        subject: str,
        body: str,
        imap_server: str,
        imap_port: int,
        imap_email: str,
        password: str,
        reply_to_id: Optional[str] = None,
        message_id: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> dict:
        """
        Create a draft in IMAP Drafts folder.
        
        Args:
            email: Recipient email
            subject: Email subject
            body: Email body (HTML or plain text)
            imap_server: IMAP server hostname
            imap_port: IMAP port (993 for SSL, 143 for STARTTLS)
            imap_email: User email for login
            password: IMAP password
            reply_to_id: Optional message ID for In-Reply-To header
            message_id: Optional message ID for References header
            attachments: Optional list of attachments
        """
        try:
            import imaplib
            from email.utils import formatdate
            
            logger.info(f"📝 Creating IMAP draft for {email}")

            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = imap_email
            message["To"] = email
            message["Subject"] = subject
            message["Date"] = formatdate(localtime=True)

            # Generate Message-ID
            msg_id = make_msgid()
            message["Message-ID"] = msg_id

            # Reply headers
            if reply_to_id:
                rfc_reply_to_id = reply_to_id if reply_to_id.startswith('<') else f"<{reply_to_id}>"
                message["In-Reply-To"] = rfc_reply_to_id

            if message_id:
                rfc_message_id = message_id if message_id.startswith('<') else f"<{message_id}>"
                message["References"] = rfc_message_id

            # Body
            if body.strip().startswith("<"):
                message.attach(MIMEText(body, "html", "utf-8"))
            else:
                message.attach(MIMEText(body, "plain", "utf-8"))

            # Attachments
            if attachments:
                for attachment in attachments:
                    filename = attachment.get('filename', 'attachment')
                    content_b64 = attachment.get('content', '')
                    content_type = attachment.get('content_type', 'application/octet-stream')
                    
                    try:
                        content_bytes = base64.b64decode(content_b64)
                        maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')
                        att_part = MIMEBase(maintype, subtype)
                        att_part.set_payload(content_bytes)
                        encoders.encode_base64(att_part)
                        att_part.add_header('Content-Disposition', 'attachment', filename=filename)
                        message.attach(att_part)
                    except Exception as att_err:
                        logger.warning(f"Failed to attach {filename}: {att_err}")

            # Connect to IMAP and append to Drafts
            if imap_port == 993:
                imap = imaplib.IMAP4_SSL(imap_server, imap_port)
            else:
                imap = imaplib.IMAP4(imap_server, imap_port)
                imap.starttls()

            imap.login(imap_email, password)

            # Try common draft folder names
            draft_folders = ["Drafts", "INBOX.Drafts", "Draft", "[Gmail]/Drafts", "Bozze"]
            draft_folder = None
            
            for folder in draft_folders:
                status, _ = imap.select(folder)
                if status == 'OK':
                    draft_folder = folder
                    break
            
            if not draft_folder:
                # Fallback: try to find drafts folder
                status, folders = imap.list()
                if status == 'OK':
                    for folder_data in folders:
                        if b'Draft' in folder_data or b'Bozze' in folder_data:
                            # Extract folder name
                            parts = folder_data.decode().split('"')
                            if len(parts) >= 2:
                                draft_folder = parts[-2]
                                break
            
            if not draft_folder:
                draft_folder = "Drafts"  # Default fallback

            # Append message to drafts folder
            import time
            import imaplib
            
            message_bytes = message.as_bytes()
            imap.append(draft_folder, '\\Draft', imaplib.Time2Internaldate(time.time()), message_bytes)

            imap.logout()

            cleaned_msg_id = _clean_message_id(msg_id)
            logger.info(f"✅ IMAP draft created successfully in {draft_folder}")

            return {
                "success": True,
                "message": f"Draft created in {draft_folder}",
                "draft_id": cleaned_msg_id,
                "notification_id": cleaned_msg_id
            }

        except Exception as e:
            logger.error(f"❌ Failed to create IMAP draft: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to create draft: {str(e)}",
                "draft_id": None,
                "notification_id": None
            }
