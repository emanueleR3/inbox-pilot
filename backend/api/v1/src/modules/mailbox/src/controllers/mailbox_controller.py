from src.core.DAO.mailbox_dao import MailboxDAO
from src.handler_exception import (
    MissingFieldException,
    NotFoundException,
    DatabaseException,
    InvalidFieldException
)
from src.modules.mailbox.src.utils.utils import validate_email_address, validate_email_addresses, validate_send_email_fields


class MailboxController:
    def __init__(self):
        self.mailbox_dao = MailboxDAO()

    def get_inbox_threads(self, payload: dict):
        box_email = payload.get("box_email")
        if not box_email:
            raise MissingFieldException(["box_email"])

        try:
            return self.mailbox_dao.fetch_inbox_threads(
                box_email=box_email,
                status=payload.get("status"),
                category=payload.get("category"),
                subcategory=payload.get("subcategory"),
                limit=payload.get("limit", 50),
                offset=payload.get("offset", 0),
            )
        except Exception as e:
            raise DatabaseException(str(e))

    def get_human_review_threads(self, email: str, limit: int, offset: int):
        try:
            return self.mailbox_dao.fetch_human_review_threads(email, limit, offset)
        except Exception as e:
            raise DatabaseException(str(e))

    def get_thread_conversation(self, thread_id: str):
        if not thread_id:
            raise MissingFieldException(["thread_id"])

        try:
            thread = self.mailbox_dao.fetch_thread_conversation(thread_id)
        except Exception as e:
            raise DatabaseException(str(e))

        if not thread:
            raise NotFoundException("Thread non trovato")

        return thread

    def get_failed_outbound_emails(self):
        try:
            return self.mailbox_dao.fetch_failed_outbound_emails()
        except Exception as e:
            raise DatabaseException(str(e))

    def get_threads_by_category(self, category: str, subcategory: str | None):
        if not category:
            raise MissingFieldException(["category"])

        try:
            return self.mailbox_dao.fetch_threads_by_category(category, subcategory)
        except Exception as e:
            raise DatabaseException(str(e))

    async def send_email(self, payload: dict):

        validate_send_email_fields(payload)

        provider = payload.get("provider", "").lower()
        email = payload.get("email")
        to = payload.get("to", [])
        subject = payload.get("subject")
        body = payload.get("body")
        cc = payload.get("cc")
        bcc = payload.get("bcc")
        reply_to = payload.get("reply_to")
        is_html = payload.get("is_html", False)

        # Valida provider
        if provider not in ["google", "microsoft"]:
            raise InvalidFieldException(
                field="provider",
                reason="deve essere 'google' o 'microsoft'"
            )

        # Valida email addresses
        validate_email_addresses(to, "to")
        if cc:
            validate_email_addresses(cc, "cc")
        if bcc:
            validate_email_addresses(bcc, "bcc")
        if reply_to:
            validate_email_address(reply_to, "reply_to")

        attachments = payload.get("attachments")

        if provider == "google":
            return await self.mailbox_dao.send_google_email(
                email=email,
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to,
                attachments=attachments,
                is_html=is_html
            )
        else:
            return await self.mailbox_dao.send_microsoft_email(
                email=email,
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to,
                attachments=attachments,
                is_html=is_html
            )
