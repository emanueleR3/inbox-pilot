from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EmailAddress(BaseModel):
    """Rappresenta un indirizzo email con nome opzionale."""
    email: str
    name: Optional[str] = None


class EmailAttachment(BaseModel):
    """Rappresenta un allegato di una email."""
    filename: str
    mime_type: Optional[str] = None
    size: Optional[int] = None


class EmailMessage(BaseModel):
    """Rappresenta un singolo messaggio email all'interno di un thread."""
    id: str
    subject: Optional[str] = None
    snippet: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    from_address: Optional[EmailAddress] = None
    to_addresses: list[EmailAddress] = Field(default_factory=list)
    cc_addresses: list[EmailAddress] = Field(default_factory=list)
    bcc_addresses: list[EmailAddress] = Field(default_factory=list)
    date: Optional[datetime] = None
    is_read: bool = False
    is_draft: bool = False
    attachments: list[EmailAttachment] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)


class EmailThread(BaseModel):
    """
    Rappresenta un thread di conversazione email.
    Contiene tutti i messaggi della conversazione, inclusi i draft.
    """
    id: str
    subject: Optional[str] = None
    snippet: Optional[str] = None
    messages: list[EmailMessage] = Field(default_factory=list)
    message_count: int = 0
    has_drafts: bool = False
    has_attachments: bool = False
    participants: list[EmailAddress] = Field(default_factory=list)
    last_message_date: Optional[datetime] = None
    is_unread: bool = False
    labels: list[str] = Field(default_factory=list)


class MailboxThreadsRequest(BaseModel):
    """Schema di richiesta per recuperare i thread della casella di posta."""
    provider: str
    token: str
    # Per IMAP
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None
    email: Optional[str] = None
    password: Optional[str] = None
    # Filtri
    time_min: Optional[datetime] = None
    time_max: Optional[datetime] = None
    max_results: Optional[int] = Field(default=50, ge=1, le=500)
    include_drafts: Optional[bool] = True
    include_spam_trash: Optional[bool] = False
    query: Optional[str] = None  # Query di ricerca (es. "from:user@example.com")
    folder: Optional[str] = "INBOX"  # Cartella da cui recuperare (INBOX, Sent, etc.)
