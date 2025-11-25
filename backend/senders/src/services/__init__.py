"""Services package for senders service."""

from .smtp_client import get_smtp_client, SMTPClient
from .send_email_service import SendEmailService
from .notification_service import NotificationService

__all__ = ["get_smtp_client", "SMTPClient", "SendEmailService", "NotificationService"]

