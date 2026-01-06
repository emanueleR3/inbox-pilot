from pydantic import BaseModel, Field 
from typing import Optional
from datetime import datetime

from realtime import List


class EmailAddress(BaseModel):
    """Rappresenta un indirizzo email con nome opzionale."""
    email: str
    name: Optional[str] = None


class EmailMessage(BaseModel):
    id: str
    subject: Optional[str] = None
    body: Optional[str] = None
    direction: str
    outcome: Optional[str] = None
    datetime: datetime
    has_attachment: bool = False
    ai_generated: bool = False
    priority_score: Optional[float] = None


class EmailThreadSummary(BaseModel):
    thread_id: str
    subject: str
    category: str
    subcategory: Optional[str] = None
    status: str
    last_message_at: datetime
    last_sender_email: str
    human_response: bool
    summary: Optional[str] = None
    email_count: int
    has_attachments: bool
    max_priority: Optional[float] = None


class EmailThreadDetail(BaseModel):
    thread_id: str
    subject: str
    messages: List[EmailMessage] = Field(default_factory=list)
    message_count: int

class FailedOutboundEmail(BaseModel):
    email_id: str
    thread_id: Optional[str]
    datetime: datetime
    outcome: str
    body: Optional[str] = None

