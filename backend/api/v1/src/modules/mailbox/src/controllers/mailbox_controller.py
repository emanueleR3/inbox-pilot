from src.core.DAO.mailbox_dao import MailboxDAO
from src.utils.utils import (
    build_google_params,
    build_microsoft_params,
    build_imap_params
)

class MailboxController:
    def __init__(self):
        self.mailbox_dao = MailboxDAO()

    async def get_email_threads(self, req: dict):

        provider = req.get("provider", "").lower()

        if provider == "google":
            params = build_google_params(req)
            return await self.mailbox_dao.fetch_gmail_threads(**params)

        if provider == "microsoft":
            params = build_microsoft_params(req)
            return await self.mailbox_dao.fetch_microsoft_threads(**params)

        params = build_imap_params(req)
        return await self.mailbox_dao.fetch_imap_threads(**params)
