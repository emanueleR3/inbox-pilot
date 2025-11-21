"""
Notification models for the notification service.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class NotificationType(str, Enum):
    """Types of notifications that can be sent."""
    HIGH_PRIORITY = "HIGH_PRIORITY"
    LOW_CONFIDENCE_CLASSIFICATION = "LOW_CONFIDENCE_CLASSIFICATION"
    EVENT_INVITE_RECEIVED = "EVENT_INVITE_RECEIVED"
    APPOINTMENT_NOT_SCHEDULED = "APPOINTMENT_NOT_SCHEDULED"


class NotificationRequest(BaseModel):
    """Request model for sending notifications."""
    notification_type: NotificationType = Field(..., description="Type of notification")
    sender_email: str = Field(..., description="Email address of the sender")
    box_email: str = Field(..., description="Email address of the mailbox")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")
    summary_attachment: Optional[str] = Field(None, description="Summary of attachments if present")
    timestamp: str = Field(..., description="Timestamp with timezone")
    overlap: Optional[bool] = Field(None, description="Whether appointment has overlap (for APPOINTMENT_NOT_SCHEDULED)")

    class Config:
        json_schema_extra = {
            "example": {
                "notification_type": "HIGH_PRIORITY",
                "sender_email": "sender@example.com",
                "box_email": "mailbox@example.com",
                "subject": "Urgent: Meeting Request",
                "body": "Please confirm the meeting...",
                "summary_attachment": "Invoice_2024.pdf - Total: €1000",
                "timestamp": "2024-11-21T10:30:00+01:00"
            }
        }


class NotificationResponse(BaseModel):
    """Response model for notification requests."""
    success: bool = Field(..., description="Whether the notification was processed successfully")
    message: str = Field(..., description="Response message")
    notification_id: Optional[str] = Field(None, description="Unique identifier for the notification")
