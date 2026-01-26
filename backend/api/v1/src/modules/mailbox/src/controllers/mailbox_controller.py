from src.core.DAO.mailbox_dao import MailboxDAO
from src.handler_exception import (
    MissingFieldException,
    NotFoundException,
    DatabaseException
)


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

    def get_human_review_threads(self, limit: int, offset: int):
        try:
            return self.mailbox_dao.fetch_human_review_threads(limit, offset)
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
