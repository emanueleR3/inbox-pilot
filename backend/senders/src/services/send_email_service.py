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
from email.utils import make_msgid
from typing import Optional
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
        message_id: Optional[str] = None
    ) -> dict:
        try:
            print("\n=== SEND EMAIL VIA GMAIL ===")
            print(f"TO: {email}")
            print(f"SUBJECT: {subject}")
            print(f"thread_id: {thread_id}")
            print(f"message_id (RFC): {message_id}")
            print("============================")

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

            # Create email
            message = MIMEMultipart('alternative')
            message['To'] = email
            message['Subject'] = subject

            if message_id:
                # Ensure message_id has angle brackets for RFC compliance
                rfc_message_id = message_id if message_id.startswith('<') else f"<{message_id}>"
                message['In-Reply-To'] = rfc_message_id
                message['References'] = rfc_message_id

            # Detect body type
            if body.strip().startswith("<") and body.strip().endswith(">"):
                part = MIMEText(body, 'html', 'utf-8')
            else:
                part = MIMEText(body, 'plain', 'utf-8')

            message.attach(part)

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
        message_id: Optional[str] = None
    ) -> dict:
        """
        Send an email using Microsoft Graph API and return RFC Message-ID (internetMessageId).
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
        
            # 2️⃣ INVIA IL MESSAGGIO
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
        
            # 3️⃣ RECUPERA l'RFC Message-ID (internetMessageId)
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
        hashed_password: str,
        reply_to_id: Optional[str] = None,
        message_id: Optional[str] = None
    ) -> dict:
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
            print("🔵 [SERVICE] hashed_password received (not printed)")

            sender_email = smtp_email

            message = MIMEMultipart("alternative")
            message["From"] = sender_email
            message["To"] = email
            message["Subject"] = subject

            msg_id = make_msgid()
            message["Message-ID"] = msg_id
            print(f"🔵 [SERVICE] Generated RFC Message-ID={msg_id}")

            if reply_to_id:
                rfc_reply_to_id = reply_to_id if reply_to_id.startswith('<') else f"<{reply_to_id}>"
                message["In-Reply-To"] = rfc_reply_to_id
                print(f"🔵 [SERVICE] In-Reply-To={rfc_reply_to_id}")

            if message_id:
                rfc_message_id = message_id if message_id.startswith('<') else f"<{message_id}>"
                message["References"] = rfc_message_id
                print(f"🔵 [SERVICE] References={rfc_message_id}")

            # HTML or text
            if body.strip().startswith("<"):
                print("🔵 [SERVICE] Body detected as HTML")
                message.attach(MIMEText(body, "html", "utf-8"))
            else:
                print("🔵 [SERVICE] Body detected as TEXT")
                message.attach(MIMEText(body, "plain", "utf-8"))

            # Decrypt password
            print("🔵 [SERVICE] Decrypting password...")
            password = decrypt(hashed_password, "pass")
            print(f"🔵 [SERVICE] Password decrypted: {'OK' if password else 'FAILED'}")

            if not password:
                raise ValueError("Failed to decrypt hashed password")

            context = ssl.create_default_context()

            print(f"🔵 [SERVICE] Selecting SMTP flow for port {smtp_port}...")

            if smtp_port == 465:
                print("🟣 [SERVICE] Connecting with SMTP_SSL...")
                with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                    print("🟣 [SERVICE] Connected via SSL")
                    server.ehlo()
                    print("🟣 [SERVICE] Logging in...")
                    server.login(sender_email, password)
                    print("🟣 [SERVICE] Login OK")
                    server.send_message(message)
                    print("🟣 [SERVICE] Message sent via SSL")

            elif smtp_port == 587:
                print("🟠 [SERVICE] Connecting on port 587 with STARTTLS...")
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

            elif smtp_port == 25:
                print("🟢 [SERVICE] Connecting on port 25...")
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.ehlo()
                    try:
                        print("🟢 [SERVICE] Trying STARTTLS (optional)...")
                        server.starttls(context=context)
                        server.ehlo()
                        print("🟢 [SERVICE] STARTTLS OK")
                    except Exception as e_tls:
                        print(f"🟡 [SERVICE] STARTTLS not available: {e_tls}")

                    try:
                        print("🟢 [SERVICE] Logging in (optional)...")
                        server.login(sender_email, password)
                        print("🟢 [SERVICE] Login OK")
                    except Exception as e_login:
                        print(f"🟡 [SERVICE] Login failed or not required: {type(e_login).__name__}: {e_login}")

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
