"""
Notification client for sending notifications to the notifications service.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional
import requests
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Get notifications service URL from environment or use default
SENDERS_URL = os.getenv("SENDERS_URL", "http://senders:8020")


class NotificationType:
    """Types of notifications that can be sent."""
    HIGH_PRIORITY = "HIGH_PRIORITY"
    LOW_CONFIDENCE_CLASSIFICATION = "LOW_CONFIDENCE_CLASSIFICATION"
    EVENT_INVITE_RECEIVED = "EVENT_INVITE_RECEIVED"
    APPOINTMENT_NOT_SCHEDULED = "APPOINTMENT_NOT_SCHEDULED"
    EVENT_FOLLOWUP_RECEIVED = "EVENT_FOLLOWUP_RECEIVED"
    INFORMATION_NOT_PRESENT = "INFORMATION_NOT_PRESENT"
    NO_AVAILABLE_SLOTS = "NO_AVAILABLE_SLOTS"
    APPOINTMENT_NOT_RESCHEDULED = "APPOINTMENT_NOT_RESCHEDULED"
    EVENT_CODE_NOT_FOUND = "EVENT_CODE_NOT_FOUND"
    CALENDAR_SERVICE_NOT_FOUND = "CALENDAR_SERVICE_NOT_FOUND"
    EVENT_DELETION_FAILED = "EVENT_DELETION_FAILED"
    EMAIL_NOT_SENT = "EMAIL_NOT_SENT"
    LOW_CONFIDENCE_WRITER = "LOW_CONFIDENCE_WRITER"
    NO_CALENDAR_PROVIDED = "NO_CALENDAR_PROVIDED"


def _convert_timestamp_to_timezone(user_timezone: str = "Europe/Rome") -> str:
    """
    Generate current timestamp converted to user's timezone.
    
    Args:
        user_timezone: User timezone string (e.g., "Europe/Rome")
        
    Returns:
        ISO format timestamp in user's timezone
    """
    try:
        now_utc = datetime.now(timezone.utc)
        target_tz = ZoneInfo(user_timezone)
        now_local = now_utc.astimezone(target_tz)
        return now_local.isoformat()
    except Exception as e:
        logger.warning(f"Failed to convert timestamp to timezone {user_timezone}: {e}")
        # Fallback to UTC
        return datetime.now(timezone.utc).isoformat()


def send_notification(
    notification_type: str,
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None,
    overlap: Optional[bool] = None
) -> bool:
    """
    Send a notification to the notifications service.
    
    Args:
        notification_type: Type of notification (HIGH_PRIORITY, LOW_CONFIDENCE_CLASSIFICATION, EVENT_INVITE_RECEIVED)
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp already in user's local timezone (defaults to current UTC time)
        overlap: Whether appointment has overlap (for APPOINTMENT_NOT_SCHEDULED)
        
    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    try:
        # Generate timestamp if not provided
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        
        # Prepare payload
        payload = {
            "notification_type": notification_type,
            "sender_email": sender_email,
            "box_email": box_email,
            "subject": subject,
            "body": body,
            "summary_attachment": summary_attachment,
            "timestamp": timestamp
        }
        
        # Add overlap if provided (for APPOINTMENT_NOT_SCHEDULED)
        if overlap is not None:
            payload["overlap"] = overlap
        
        # Send request to senders service
        endpoint = f"{SENDERS_URL}/notification/send"
        logger.info(f"📤 Sending notification to {endpoint} - Type: {notification_type}")
        
        response = requests.post(
            endpoint,
            json=payload,   
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"✅ Notification sent successfully - ID: {result.get('notification_id')}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to send notification: {str(e)}")
        # Don't raise exception - notifications failing shouldn't break the workflow
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error sending notification: {str(e)}")
        return False

def send_event_followup_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send an event follow-up notification.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.EVENT_FOLLOWUP_RECEIVED,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )

def send_high_priority_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send a high priority notification.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.HIGH_PRIORITY,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )


def send_low_confidence_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send a low confidence classification notification.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.LOW_CONFIDENCE_CLASSIFICATION,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )


def send_event_invite_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send an event invite received notification.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.EVENT_INVITE_RECEIVED,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )


def send_appointment_not_scheduled_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    overlap: Optional[bool] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send an appointment not scheduled notification.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        overlap: Whether there was an overlap with existing appointments
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.APPOINTMENT_NOT_SCHEDULED,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        overlap=overlap,
        timestamp=timestamp
    )


def send_information_not_present_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send a notification when company information is not present in the database.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.INFORMATION_NOT_PRESENT,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )


def send_no_available_slots_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send a notification when no available slots are found for appointment.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.NO_AVAILABLE_SLOTS,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )


def send_appointment_not_rescheduled_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send a notification when appointment could not be rescheduled.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.APPOINTMENT_NOT_RESCHEDULED,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )


def send_event_code_not_found_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send a notification when event code is not found in database.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.EVENT_CODE_NOT_FOUND,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )


def send_calendar_service_not_found_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send a notification when calendar service is not found for user.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.CALENDAR_SERVICE_NOT_FOUND,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )


def send_event_deletion_failed_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send a notification when event deletion fails.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.EVENT_DELETION_FAILED,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )


def send_email_not_sent_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send a notification when an email could not be sent.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.EMAIL_NOT_SENT,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )


def send_low_confidence_writer_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send a notification when the writer has low confidence.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.LOW_CONFIDENCE_WRITER,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )

def send_no_calendar_provided_notification(
    sender_email: str,
    box_email: str,
    subject: str,
    body: str,
    summary_attachment: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Send a notification when no calendar is provided.
    
    Args:
        sender_email: Email address of the sender
        box_email: Email address of the mailbox
        subject: Email subject
        body: Email body content
        summary_attachment: Summary of attachments if present
        timestamp: Timestamp in user's local timezone
        
    Returns:
        bool: True if notification was sent successfully
    """
    return send_notification(
        notification_type=NotificationType.NO_CALENDAR_PROVIDED,
        sender_email=sender_email,
        box_email=box_email,
        subject=subject,
        body=body,
        summary_attachment=summary_attachment,
        timestamp=timestamp
    )
