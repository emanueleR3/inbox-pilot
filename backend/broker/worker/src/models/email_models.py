"""
Data models for email processing.
Defines the structure for emails, threads, and processing metadata.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class EmailProvider(Enum):
    """Email provider types."""
    GMAIL = "gmail"
    MICROSOFT = "microsoft"
    IMAP = "imap"


class ProcessingStatus(Enum):
    """Email processing status."""
    PENDING = "pending"
    FILTERED = "filtered"
    PROCESSED = "processed"
    AI_PROCESSING = "ai_processing"
    HUMAN_RESPONSE = "human_response"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EmailMessage:
    """
    Standardized email message model.
    """
    # Basic email fields
    provider: EmailProvider
    user_email: str
    message_id: str
    reply_to_id: str
    subject: Optional[str]
    from_address: str
    to_address: Optional[str]
    cc_address: Optional[str]
    bcc_address: Optional[str]
    date: Optional[str]
    body_text: Optional[str]
    body_html: Optional[str]
    timestamp: Optional[str]
    
    # Provider-specific fields
    labels: List[str]
    attachments: List[Dict[str, Any]]
    raw_data: Optional[str]
    
    # Processing metadata
    no_reply: bool = False
    is_sent: bool = False
    is_ai_generated: bool = False
    needs_human_response: bool = False
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    
    # Thread information
    unified_thread_id: Optional[str] = None
    thread_started_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    
    # Additional metadata
    subscription_id: Optional[str] = None
    folder_type: Optional[str] = None
    size: Optional[int] = None
    charset: Optional[str] = None
    content_type: Optional[str] = None


@dataclass
class EmailThread:
    """
    Unified email thread model that works across providers.
    """
    # Thread identification
    unified_thread_id: str
    user_email: str
    subject: str
    
    # Thread metadata
    started_at: datetime
    last_message_at: datetime
    last_message_id: str
    last_sender_email: str
    
    # Participants
    sender_emails: List[str]
    cc_emails: List[str]
    
    # Thread state
    message_count: int = 0
    human_response: bool = False
    ai_summary: Optional[str] = None
    category: Optional[str] = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    
    # Provider-specific thread IDs (for cross-reference)
    provider_thread_ids: Dict[str, str] = None
    
    # Attachments
    attachment_emails_id: List[str] = None


@dataclass
class ProcessingResult:
    """
    Result of email processing operation.
    """
    success: bool
    message_id: str
    reply_to_id: Optional[str]
    processing_status: ProcessingStatus
    needs_ai_processing: bool = False
    needs_human_response: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None