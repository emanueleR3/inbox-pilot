"""
Routers package for the senders service.
"""

from .notification_router import router as notification_router

__all__ = ["notification_router"]
