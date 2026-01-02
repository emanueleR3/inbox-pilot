from typing import Optional
from datetime import datetime
from src.core.DAO.mailbox_dao import MailboxDAO
from src.handler_exception import (
    InvalidFieldException, 
    MissingFieldException,
    BadRequestException
)


class MailboxController:
    def __init__(self):
        self.mailbox_dao = MailboxDAO()

    async def get_email_threads(self, req: dict):
        self._validate_required_fields(req)

        provider = req.get("provider", "").lower()
        
        if provider not in ["google", "microsoft", "imap"]:
            raise InvalidFieldException(
                field="provider",
                reason="deve essere 'google', 'microsoft' o 'imap'"
            )

        max_results = req.get("max_results", 50)
        if not isinstance(max_results, int) or max_results < 1 or max_results > 500:
            raise InvalidFieldException(
                field="max_results",
                reason="deve essere un intero tra 1 e 500"
            )

        time_min = self._parse_datetime_field(req.get("time_min"), "time_min")
        time_max = self._parse_datetime_field(req.get("time_max"), "time_max")

        if time_min and time_max and time_min >= time_max:
            raise InvalidFieldException(
                field="time_min/time_max",
                reason="time_min deve essere precedente a time_max"
            )

        include_drafts = req.get("include_drafts", True)
        if not isinstance(include_drafts, bool):
            raise InvalidFieldException(
                field="include_drafts",
                reason="deve essere un valore booleano"
            )

        include_spam_trash = req.get("include_spam_trash", False)
        if not isinstance(include_spam_trash, bool):
            raise InvalidFieldException(
                field="include_spam_trash",
                reason="deve essere un valore booleano"
            )

        if provider == "google":
            return await self._handle_google(req, time_min, time_max, max_results, include_drafts, include_spam_trash)
        elif provider == "microsoft":
            return await self._handle_microsoft(req, time_min, time_max, max_results, include_drafts, include_spam_trash)
        else:
            return await self._handle_imap(req, time_min, time_max, max_results, include_drafts)

    async def _handle_google(
        self,
        req: dict,
        time_min: Optional[datetime],
        time_max: Optional[datetime],
        max_results: int,
        include_drafts: bool,
        include_spam_trash: bool
    ):
        """Gestisce le richieste per Gmail."""
        token = req.get("token")
        if not token:
            raise MissingFieldException(fields=["token"])

        query = req.get("query")

        return await self.mailbox_dao.fetch_gmail_threads(
            token=token,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
            include_drafts=include_drafts,
            include_spam_trash=include_spam_trash,
            query=query
        )

    async def _handle_microsoft(
        self,
        req: dict,
        time_min: Optional[datetime],
        time_max: Optional[datetime],
        max_results: int,
        include_drafts: bool,
        include_spam_trash: bool
    ):
        """Gestisce le richieste per Microsoft."""
        token = req.get("token")
        if not token:
            raise MissingFieldException(fields=["token"])

        folder = req.get("folder", "inbox")

        return await self.mailbox_dao.fetch_microsoft_threads(
            token=token,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
            include_drafts=include_drafts,
            include_spam_trash=include_spam_trash,
            folder=folder
        )

    async def _handle_imap(
        self,
        req: dict,
        time_min: Optional[datetime],
        time_max: Optional[datetime],
        max_results: int,
        include_drafts: bool
    ):
        """Gestisce le richieste per IMAP."""
        # Validazione campi IMAP specifici
        imap_server = req.get("imap_server")
        imap_port = req.get("imap_port")
        email_address = req.get("email")
        password = req.get("password")

        missing = []
        if not imap_server:
            missing.append("imap_server")
        if not imap_port:
            missing.append("imap_port")
        if not email_address:
            missing.append("email")
        if not password:
            missing.append("password")

        if missing:
            raise MissingFieldException(fields=missing)

        # Validazione porta
        if not isinstance(imap_port, int) or imap_port < 1 or imap_port > 65535:
            raise InvalidFieldException(
                field="imap_port",
                reason="deve essere un intero tra 1 e 65535"
            )

        folder = req.get("folder", "INBOX")

        return await self.mailbox_dao.fetch_imap_threads(
            imap_server=imap_server,
            imap_port=imap_port,
            email_address=email_address,
            password=password,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
            include_drafts=include_drafts,
            folder=folder
        )

    def _validate_required_fields(self, request_data: dict) -> None:
        """Valida che i campi obbligatori siano presenti."""
        if not request_data.get("provider"):
            raise MissingFieldException(fields=["provider"])

    def _parse_datetime_field(
        self, 
        value: Optional[str], 
        field_name: str
    ) -> Optional[datetime]:
        """Parsa un campo datetime ISO 8601."""
        if value is None:
            return None

        if not isinstance(value, str):
            raise InvalidFieldException(
                field=field_name,
                reason="deve essere una stringa in formato ISO 8601"
            )

        try:
            if value.endswith("Z"):
                value = value.replace("Z", "+00:00")

            return datetime.fromisoformat(value)
        except (ValueError, AttributeError):
            raise InvalidFieldException(
                field=field_name,
                reason="formato data/ora non valido. Utilizzare formato ISO 8601 (es. 2025-01-15T10:00:00Z)"
            )

