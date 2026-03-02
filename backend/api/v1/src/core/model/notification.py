from pydantic import BaseModel
from datetime import datetime as dt
from typing import Optional
from uuid import UUID


class NotificationBase(BaseModel):
    """Model base per una notifica."""
    notification_id: UUID
    text: Optional[str] = None
    type: Optional[str] = None
    email: str
    email_id: Optional[UUID] = None
    view: bool = False

    class Config:
        from_attributes = True


class EmailData(BaseModel):
    """Model per i dati dell'email associata alla notifica."""
    body: Optional[str] = None
    datetime: Optional[dt] = None
    message_id: Optional[str] = None
    outcome: Optional[str] = None
    direction: Optional[str] = None
    has_attachment: Optional[bool] = False

    class Config:
        from_attributes = True


class NotificationWithEmail(BaseModel):
    """Model per una notifica con i dati dell'email inclusi."""
    notification_id: UUID
    text: Optional[str] = None
    type: Optional[str] = None
    email: str
    email_id: Optional[UUID] = None
    view: bool = False
    email_data: Optional[EmailData] = None

    class Config:
        from_attributes = True
