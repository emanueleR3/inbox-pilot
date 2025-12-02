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
            print(f"[DEBUG] Access token decrypted: {bool(access_token)}")

            if not access_token:
                raise ValueError("Failed to decrypt access token")

            scopes_env = os.getenv("GOOGLE_SCOPES", "")
            print(f"[DEBUG] GOOGLE_SCOPES env: {scopes_env}")

            if scopes_env:
                scopes = [scope.strip() for scope in scopes_env.split() if scope.strip()]
            else:
                scopes = [
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.modify",
                ]

            print(f"[DEBUG] Final scopes: {scopes}")

            creds = Credentials(
                token=access_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                scopes=scopes
            )

            service = build('gmail', 'v1', credentials=creds)
            print("[DEBUG] Gmail service built successfully")

            # Create email
            message = MIMEMultipart('alternative')
            message['To'] = email
            message['Subject'] = subject

            if message_id:
                # Ensure message_id has angle brackets for RFC compliance
                rfc_message_id = message_id if message_id.startswith('<') else f"<{message_id}>"
                print(f"[DEBUG] Adding In-Reply-To and References headers -> {rfc_message_id}")
                message['In-Reply-To'] = rfc_message_id
                message['References'] = rfc_message_id
            else:
                print("[DEBUG] No message_id given — sending as NEW email")

            # Detect body type
            if body.strip().startswith("<") and body.strip().endswith(">"):
                print("[DEBUG] Body detected as HTML")
                part = MIMEText(body, 'html', 'utf-8')
            else:
                print("[DEBUG] Body detected as PLAIN TEXT")
                part = MIMEText(body, 'plain', 'utf-8')

            message.attach(part)

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            print(f"[DEBUG] Raw message length: {len(raw_message)}")

            message_body = {"raw": raw_message}

            if thread_id:
                print(f"[DEBUG] Adding threadId to send body: {thread_id}")
                message_body["threadId"] = thread_id
            else:
                print("[DEBUG] No threadId given — Gmail may create new thread")

            print("[DEBUG] Sending email...")

            send_result = service.users().messages().send(
                userId='me',
                body=message_body
            ).execute()

            gmail_internal_id = send_result.get("id")
            print(f"[DEBUG] Gmail send() result ID: {gmail_internal_id}")

            # Retrieve RFC Message-ID
            rfc_message_id = None

            try:
                print("[DEBUG] Fetching Message-ID from Gmail...")

                msg = service.users().messages().get(
                    userId="me",
                    id=gmail_internal_id,
                    format="metadata",
                    metadataHeaders=["Message-ID", "Message-Id"]
                ).execute()

                print("[DEBUG] Received metadata headers:")

                for h in msg.get("payload", {}).get("headers", []):
                    print(f"   - {h.get('name')}: {h.get('value')}")
                    if h.get("name", "").lower() == "message-id":
                        rfc_message_id = h.get("value")

                print(f"[DEBUG] Extracted RFC Message-ID: {rfc_message_id}")

            except Exception as err:
                print(f"[DEBUG] Could not fetch RFC Message-ID: {err}")

            print("=== EMAIL SENT SUCCESSFULLY ===\n")

            return {
                "success": True,
                "message": f"Email sent to {email}",
                "notification_id": gmail_internal_id,
                "message_id": rfc_message_id
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
        
            return {
                "success": True,
                "message": f"Email sent successfully via Microsoft to {email}",
                "notification_id": msg_id,       # id interno Graph del messaggio
                "message_id": rfc_message_id     # RFC Message-ID (internetMessageId)
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
        smtp_password: str,
        reply_to_id: Optional[str] = None,
        message_id: Optional[str] = None
    ) -> dict:
        try:
            sender_email = smtp_email

            message = MIMEMultipart("alternative")
            message["From"] = sender_email
            message["To"] = email
            message["Subject"] = subject
        
            # 🆕 Genero Message-ID RFC e lo aggiungo all'header
            msg_id = make_msgid()
            message["Message-ID"] = msg_id

            if reply_to_id:
                # Ensure reply_to_id has angle brackets for RFC compliance
                rfc_reply_to_id = reply_to_id if reply_to_id.startswith('<') else f"<{reply_to_id}>"
                message["In-Reply-To"] = rfc_reply_to_id
            if message_id:
                # Ensure message_id has angle brackets for RFC compliance
                rfc_message_id = message_id if message_id.startswith('<') else f"<{message_id}>"
                message["References"] = rfc_message_id

            # HTML o testo
            if body.strip().startswith("<"):
                message.attach(MIMEText(body, "html", "utf-8"))
            else:
                message.attach(MIMEText(body, "plain", "utf-8"))

            # SSL/STARTTLS
            context = ssl.create_default_context()

            password = decrypt(smtp_password, "pass")
            if not password:
                raise ValueError("Failed to decrypt hashed password")

            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                    server.ehlo()
                    server.login(sender_email, password)
                    server.send_message(message)

            elif smtp_port == 587:
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(sender_email, password)
                    server.send_message(message)

            elif smtp_port == 25:
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.ehlo()
                    try:
                        server.starttls(context=context)
                        server.ehlo()
                    except:
                        pass

                    try:
                        server.login(sender_email, password)
                    except:
                        pass

                    server.send_message(message)

            else:
                return {
                    "success": False,
                    "message": f"Unsupported SMTP port {smtp_port}. Use 465 / 587 / 25.",
                    "message_id": None
                }

            return {
                "success": True,
                "message": "Email sent",
                "message_id": msg_id,     # 🆕 RFC Message-ID
                "notification_id": msg_id  # Per uniformità con gli altri metodi
            }

        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "message_id": None,
                "notification_id": None
            }