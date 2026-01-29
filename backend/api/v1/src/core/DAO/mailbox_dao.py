from typing import List, Optional
import httpx
import base64
import json

from src.core.database import get_supabase_client
from src.core.model.mailbox import (
    EmailMessage,
    EmailThreadDetail,
    EmailThreadSummary,
    FailedOutboundEmail,
    SendEmailResponse,
    EmailAttachment
)
from src.core.utils.utils import decrypt_token, build_mime_message
from src.handler_exception import (
    GmailAPIException,
    GraphAPIException,
    InvalidTokenException
)


class MailboxDAO:
    def __init__(self):
        self.supabase = get_supabase_client()

    def fetch_inbox_threads(
        self,
        box_email: str,
        status: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[EmailThreadSummary]:

        query = self.supabase.table("inbox_view").select("*").eq("box_email", box_email)

        if status:
            query = query.eq("status", status)
        if category:
            query = query.eq("category", category)
        if subcategory:
            query = query.eq("subcategory", subcategory)

        rows = (
            query
            .order("last_message_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
            .data
        )

        return [
            EmailThreadSummary(
                thread_id=row["thread_id"],
                subject=row["subject"],
                category=row["category"],
                subcategory=row.get("subcategory"),
                status=row["status"],
                last_message_at=row["last_message_at"],
                last_sender_email=row["last_sender_email"],
                human_response=row["human_response"],
                summary=row.get("summary"),
                email_count=row["email_count"],
                has_attachments=row["has_attachments"],
                max_priority=row.get("max_priority")
            )
            for row in rows
        ]

    def fetch_human_review_threads(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[EmailThreadSummary]:

        rows = (
            self.supabase
            .table("inbox_human_review_view")
            .select("*")
            .order("last_message_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
            .data
        )

        return [
            EmailThreadSummary(
                thread_id=row["thread_id"],
                subject=row["subject"],
                category=row["category"],
                subcategory=row.get("subcategory"),
                status=row["status"],
                last_message_at=row["last_message_at"],
                last_sender_email=row["last_sender_email"],
                human_response=row["human_response"],
                summary=row.get("summary"),
                email_count=row["email_count"],
                has_attachments=row["has_attachments"],
                max_priority=row.get("max_priority")
            )
            for row in rows
        ]

    def fetch_thread_conversation(
        self,
        thread_id: str
    ) -> Optional[EmailThreadDetail]:

        rows = (
            self.supabase
            .table("thread_conversation_view")
            .select("*")
            .eq("thread_id", thread_id)
            .order("datetime", desc=False)
            .execute()
            .data
        )

        if not rows:
            return None

        messages = [
            EmailMessage(
                id=row["email_id"],
                subject=row.get("subject"),
                body=row.get("body"),
                direction=row["direction"],
                outcome=row.get("outcome"),
                datetime=row["datetime"],
                has_attachment=row["has_attachment"],
                ai_generated=row["ai_generated"],
                priority_score=row.get("priority_score")
            )
            for row in rows
        ]

        return EmailThreadDetail(
            thread_id=thread_id,
            subject=rows[0]["subject"],
            messages=messages,
            message_count=len(messages)
        )

    def fetch_failed_outbound_emails(self) -> List[FailedOutboundEmail]:

        rows = (
            self.supabase
            .table("failed_outbound_emails_view")
            .select("*")
            .order("datetime", desc=True)
            .execute()
            .data
        )

        return [
            FailedOutboundEmail(
                email_id=row["email_id"],
                thread_id=row.get("thread_id"),
                datetime=row["datetime"],
                outcome=row["outcome"],
                body=row.get("body")
            )
            for row in rows
        ]

    def fetch_threads_by_category(
        self,
        category: str,
        subcategory: Optional[str] = None
    ) -> List[EmailThreadSummary]:

        query = self.supabase.table("inbox_view").select("*").eq("category", category)

        if subcategory:
            query = query.eq("subcategory", subcategory)

        rows = (
            query
            .order("last_message_at", desc=True)
            .execute()
            .data
        )

        return [
            EmailThreadSummary(
                thread_id=row["thread_id"],
                subject=row["subject"],
                category=row["category"],
                subcategory=row.get("subcategory"),
                status=row["status"],
                last_message_at=row["last_message_at"],
                last_sender_email=row["last_sender_email"],
                human_response=row["human_response"],
                summary=row.get("summary"),
                email_count=row["email_count"],
                has_attachments=row["has_attachments"],
                max_priority=row.get("max_priority")
            )
            for row in rows
        ]

    async def send_google_email(
        self,
        email: str,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
        is_html: bool = False
    ) -> SendEmailResponse:
        
        token = (
            self.supabase
            .table("subscription_services")
            .select("hashed_access_token")
            .eq("email", email)
            .execute()
        )

        if not token.data:
            raise InvalidTokenException(provider="Google")

        encrypted_token = token.data[0]["hashed_access_token"]
        decrypted_token = decrypt_token(encrypted_token, "token")

        # Costruisci il messaggio email in formato MIME
        message = build_mime_message(
            from_email=email,
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            attachments=attachments,
            is_html=is_html
        )

        # Encode in base64 URL-safe
        raw_message = base64.urlsafe_b64encode(message.encode()).decode()

        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Content-Type": "application/json"
        }
        payload = {"raw": raw_message}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, 
                    headers=headers, 
                    json=payload, 
                    timeout=30.0
                )

                if response.status_code == 401:
                    raise InvalidTokenException(provider="Google")

                if response.status_code != 200:
                    raise GmailAPIException(
                        reason=f"Status code {response.status_code}: {response.text}"
                    )

                result = response.json()
                return SendEmailResponse(
                    success=True,
                    message_id=result.get("id"),
                    message="Email inviata con successo"
                )

        except httpx.TimeoutException:
            raise GmailAPIException(reason="Timeout durante l'invio dell'email")
        except httpx.RequestError as e:
            raise GmailAPIException(reason=f"Errore di connessione: {str(e)}")
        except InvalidTokenException:
            raise
        except GmailAPIException:
            raise
        except Exception as e:
            raise GmailAPIException(reason=f"Errore inaspettato: {str(e)}")

    # =========================================================================
    # INVIO EMAIL - MICROSOFT (GRAPH API)
    # =========================================================================

    async def send_microsoft_email(
        self,
        email: str,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
        is_html: bool = False
    ) -> SendEmailResponse:
        """Invia una email tramite Microsoft Graph API."""
        
        token = (
            self.supabase
            .table("subscription_services")
            .select("hashed_access_token")
            .eq("email", email)
            .execute()
        )

        if not token.data:
            raise InvalidTokenException(provider="Microsoft")

        encrypted_token = token.data[0]["hashed_access_token"]
        decrypted_token = decrypt_token(encrypted_token, "token")

        # Costruisci il payload per Microsoft Graph
        message_payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML" if is_html else "Text",
                    "content": body
                },
                "toRecipients": [
                    {"emailAddress": {"address": addr}} for addr in to
                ]
            },
            "saveToSentItems": True
        }

        if cc:
            message_payload["message"]["ccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in cc
            ]
        
        if bcc:
            message_payload["message"]["bccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in bcc
            ]

        if reply_to:
            message_payload["message"]["replyTo"] = [
                {"emailAddress": {"address": reply_to}}
            ]

        if attachments:
            message_payload["message"]["attachments"] = [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": att.get("filename"),
                    "contentType": att.get("content_type", "application/octet-stream"),
                    "contentBytes": att.get("content")
                }
                for att in attachments
            ]

        url = "https://graph.microsoft.com/v1.0/me/sendMail"
        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, 
                    headers=headers, 
                    json=message_payload, 
                    timeout=30.0
                )

                if response.status_code == 401:
                    raise InvalidTokenException(provider="Microsoft")

                if response.status_code not in [200, 202]:
                    raise GraphAPIException(
                        reason=f"Status code {response.status_code}: {response.text}"
                    )

                return SendEmailResponse(
                    success=True,
                    message_id=None,  # Microsoft non restituisce message_id per sendMail
                    message="Email inviata con successo"
                )

        except httpx.TimeoutException:
            raise GraphAPIException(reason="Timeout durante l'invio dell'email")
        except httpx.RequestError as e:
            raise GraphAPIException(reason=f"Errore di connessione: {str(e)}")
        except InvalidTokenException:
            raise
        except GraphAPIException:
            raise
        except Exception as e:
            raise GraphAPIException(reason=f"Errore inaspettato: {str(e)}")




