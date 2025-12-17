from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO
from src.modules.auth.src.utils.custom_provider import test_imap_connection, test_imap_login, test_smtp_connection, test_smtp_login
from src.handler_exception import (
    MissingFieldException,
    InvalidPortException,
    InvalidEmailException,
    DatabaseException,
    APIException
)


class CustomProviderController:

    def custom_provider_login(payload: dict):
        server_imap = payload.get("server_imap")
        server_smtp = payload.get("server_smtp")
        imap_port = payload.get("imap_port")
        smtp_port = payload.get("smtp_port")
        email = payload.get("email")
        password = payload.get("password")
        subscription_id = payload.get("subscription_id")
        calendar_provider = payload.get("calendar_provider")

        missing_fields = []
        if not server_imap:
            missing_fields.append("server_imap")
        if not server_smtp:
            missing_fields.append("server_smtp")
        if not email:
            missing_fields.append("email")
        if not password:
            missing_fields.append("password")

        if missing_fields:
            raise MissingFieldException(fields=missing_fields)

        if imap_port and not isinstance(imap_port, int):
            raise InvalidPortException(port_type="porta IMAP")
        if smtp_port and not isinstance(smtp_port, int):
            raise InvalidPortException(port_type="porta SMTP")

        if "@" not in email:
            raise InvalidEmailException(email=email)

        test_imap_connection(server_imap, imap_port)
        test_imap_login(server_imap, imap_port, email, password)
        test_smtp_connection(server_smtp, smtp_port)
        test_smtp_login(server_smtp, smtp_port, email, password)

        try:
            res = SubscriptionServiceDAO().save_custom_provider_credentials(
                server_imap, server_smtp, imap_port, smtp_port, email, password,
                subscription_id, calendar_provider
            )
            return res

        except APIException:
            raise
        except Exception:
            raise DatabaseException(operation="salvataggio credenziali custom provider")


