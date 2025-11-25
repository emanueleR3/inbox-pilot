"""Models package for senders service."""

from .models import NotificationRequest, NotificationResponse, NotificationType
from .email_templates import get_email_template

__all__ = [
    "NotificationRequest",
    "NotificationResponse", 
    "NotificationType",
    "get_email_template"
]
