from src.core.DAO.mailbox_dao import MailboxDAO
from src.handler_exception import (
    MissingFieldException,
    InvalidFieldException,
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

        return self.mailbox_dao.fetch_inbox_threads(payload)

    def get_human_review_threads(self, limit: int, offset: int):
        return self.mailbox_dao.fetch_human_review_threads(limit, offset)

    def get_thread_conversation(self, thread_id: str):
        if not thread_id:
            raise MissingFieldException(["thread_id"])

        thread = self.mailbox_dao.fetch_thread_conversation(thread_id)
        if not thread:
            raise NotFoundException("Thread non trovato")

        return thread

    def get_failed_outbound_emails(self):
        return self.mailbox_dao.fetch_failed_outbound_emails()

    def get_threads_by_category(self, category: str, subcategory: str | None):
        if not category:
            raise MissingFieldException(["category"])

        return self.mailbox_dao.fetch_threads_by_category(category, subcategory)


    