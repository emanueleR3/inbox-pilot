from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class EmailAttachment(BaseModel):
    """Model per rappresentare un attachment email dal database."""
    attachment_id: UUID
    thread_id: Optional[UUID] = None
    email_id: UUID
    sender: str
    file_name: str
    file_path: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    service_id: Optional[UUID] = None
    file_hash: str
    receiver: str
    cc: Optional[List[str]] = None

    class Config:
        from_attributes = True


class EmailAttachmentRead(BaseModel):
    """Model per la lettura di un attachment (senza dati sensibili come file_path)."""
    attachment_id: UUID
    thread_id: Optional[UUID] = None
    email_id: UUID
    sender: str
    file_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    service_id: Optional[UUID] = None
    receiver: str
    cc: Optional[List[str]] = None

    class Config:
        from_attributes = True
