"""
Notification Router - Handles notification webhook endpoints.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status

from ..models import NotificationRequest, NotificationResponse
from ..db_client import get_user_email_from_box_email
from ..gmail_client import get_gmail_client
from ..email_templates import get_email_template

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/notification",
    tags=["notification"]
)


@router.post("/send", response_model=NotificationResponse)
async def send_notification(notification: NotificationRequest):
    """
    Webhook endpoint to receive notification requests from automations service.
    
    Args:
        notification: NotificationRequest containing all notification details
        
    Returns:
        NotificationResponse with success status and message
    """
    try:
        logger.info(f"📬 Received notification request - Type: {notification.notification_type}")
        
        # Step 1: Retrieve user email from box_email
        user_email = get_user_email_from_box_email(notification.box_email)
        
        if not user_email:
            logger.warning(f"⚠️ Could not find user email for box_email: {notification.box_email}")
            # Continue anyway for debugging purposes
            user_email = "NOT_FOUND"
        
        # Debug: Print the complete payload
        print("\n" + "="*80)
        print("🔔 NOTIFICATION RECEIVED ")
        print("="*80)
        print(f"Type:              {notification.notification_type}")
        print(f"Sender Email:      {notification.sender_email}")
        print(f"Box Email:         {notification.box_email}")
        print(f"👤 USER TO NOTIFY: {user_email}")
        print(f"Subject:           {notification.subject}")
        print(f"Timestamp:         {notification.timestamp}")
        
        # Print overlap if present (for APPOINTMENT_NOT_SCHEDULED)
        if notification.overlap is not None:
            print(f"Overlap:           {notification.overlap}")
        
        print(f"\nBody Preview:")
        print("-" * 80)
        print(notification.body[:500] + "..." if len(notification.body) > 500 else notification.body)
        print("-" * 80)
        
        if notification.summary_attachment:
            print(f"\nAttachment Summary:")
            print("-" * 80)
            print(notification.summary_attachment)
            print("-" * 80)
        
        print("="*80 + "\n")
        
        # Step 2: Generate email HTML template
        email_subject = f"🔔 Corretto AI - {notification.notification_type.replace('_', ' ').title()}"
        html_body = get_email_template(
            notification_type=notification.notification_type,
            sender_email=notification.sender_email,
            subject=notification.subject,
            body=notification.body,
            timestamp=notification.timestamp,
            overlap=notification.overlap,
            summary_attachment=notification.summary_attachment
        )
        
        # Step 3: Send email via Gmail API
        gmail_client = get_gmail_client()
        email_sent = gmail_client.send_email(
            to_email=user_email,
            subject=email_subject,
            html_body=html_body
        )
        
        # Generate a unique notification ID (for future tracking)
        notification_id = f"notif_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        if email_sent:
            logger.info(f"✅ Notification processed and email sent successfully - ID: {notification_id}")
            return NotificationResponse(
                success=True,
                message=f"Notification email sent successfully to {user_email}",
                notification_id=notification_id
            )
        else:
            logger.warning(f"⚠️ Notification processed but email failed to send - ID: {notification_id}")
            return NotificationResponse(
                success=False,
                message=f"Failed to send notification email to {user_email}",
                notification_id=notification_id
            )
        
    except Exception as e:
        logger.error(f"❌ Error processing notification: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process notification: {str(e)}"
        )
