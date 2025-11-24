"""
Routers package for the senders service.
"""
from .notification_router import router as notification_router
from .send_email_router import router as send_email_router

__all__ = ["notification_router", "send_email_router"]
