"""
Notification service for handling notification email sending.
Encapsulates business logic for processing and sending notification emails.
"""

import logging
from datetime import datetime
from typing import Optional

from ..db.db_client import get_user_email_from_box_email
from ..services.smtp_client import get_smtp_client
from ..models.email_templates import get_email_template

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for processing and sending notification emails."""
    
    def __init__(self):
        """Initialize the notification service."""
        self.smtp_client = get_smtp_client()
    
    def send_notification(
        self,
        notification_type: str,
        sender_email: str,
        box_email: str,
        subject: str,
        body: str,
        timestamp: str,
        summary_attachment: Optional[str] = None,
        overlap: Optional[bool] = None
    ) -> dict:
        """
        Process and send a notification email.
        
        Args:
            notification_type: Type of notification
            sender_email: Email address of the sender
            box_email: Email address of the mailbox
            subject: Email subject
            body: Email body content
            timestamp: Timestamp with timezone
            summary_attachment: Optional summary of attachments
            overlap: Optional overlap flag for appointments
            
        Returns:
            dict: Response with success status, message, and notification_id
        """
        try:
            logger.info(f"📬 Processing notification - Type: {notification_type}")
            
            # Step 1: Retrieve user email from box_email
            user_email = get_user_email_from_box_email(box_email)
            
            if not user_email:
                logger.warning(f"⚠️ Could not find user email for box_email: {box_email}")
                # Continue anyway for debugging purposes
                user_email = "NOT_FOUND"
            
            # Debug: Print the complete payload
            self._log_notification_details(
                notification_type=notification_type,
                sender_email=sender_email,
                box_email=box_email,
                user_email=user_email,
                subject=subject,
                body=body,
                timestamp=timestamp,
                overlap=overlap,
                summary_attachment=summary_attachment
            )
            
            # Step 2: Generate email HTML template
            email_subject = f"🔔 Corretto AI - {notification_type.replace('_', ' ').title()}"
            html_body = get_email_template(
                notification_type=notification_type,
                sender_email=sender_email,
                subject=subject,
                body=body,
                timestamp=timestamp,
                overlap=overlap,
                summary_attachment=summary_attachment
            )
            
            # Step 3: Send email via SMTP
            email_sent = self.smtp_client.send_email(
                to_email=user_email,
                subject=email_subject,
                html_body=html_body
            )
            
            # Generate a unique notification ID (for future tracking)
            notification_id = f"notif_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            
            if email_sent:
                logger.info(f"✅ Notification processed and email sent successfully - ID: {notification_id}")
                return {
                    "success": True,
                    "message": f"Notification email sent successfully to {user_email}",
                    "notification_id": notification_id
                }
            else:
                logger.warning(f"⚠️ Notification processed but email failed to send - ID: {notification_id}")
                return {
                    "success": False,
                    "message": f"Failed to send notification email to {user_email}",
                    "notification_id": notification_id
                }
            
        except Exception as e:
            logger.error(f"❌ Error processing notification: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to process notification: {str(e)}",
                "notification_id": None
            }
    
    def _log_notification_details(
        self,
        notification_type: str,
        sender_email: str,
        box_email: str,
        user_email: str,
        subject: str,
        body: str,
        timestamp: str,
        overlap: Optional[bool],
        summary_attachment: Optional[str]
    ):
        """Log detailed notification information for debugging."""
        print("\n" + "="*80)
        print("🔔 NOTIFICATION RECEIVED ")
        print("="*80)
        print(f"Type:              {notification_type}")
        print(f"Sender Email:      {sender_email}")
        print(f"Box Email:         {box_email}")
        print(f"👤 USER TO NOTIFY: {user_email}")
        print(f"Subject:           {subject}")
        print(f"Timestamp:         {timestamp}")
        
        # Print overlap if present (for APPOINTMENT_NOT_SCHEDULED)
        if overlap is not None:
            print(f"Overlap:           {overlap}")
        
        print(f"\nBody Preview:")
        print("-" * 80)
        print(body[:500] + "..." if len(body) > 500 else body)
        print("-" * 80)
        
        if summary_attachment:
            print(f"\nAttachment Summary:")
            print("-" * 80)
            print(summary_attachment)
            print("-" * 80)
        
        print("="*80 + "\n")
