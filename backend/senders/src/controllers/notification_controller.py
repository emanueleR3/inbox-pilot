"""
Notification controller for handling HTTP requests.
Validates input and delegates to notification service.
"""

from fastapi import HTTPException, status
from ..services.notification_service import NotificationService


class NotificationController:
    """Controller for notification endpoints."""
    
    def __init__(self):
        """Initialize the controller with notification service."""
        self.notification_service = NotificationService()
    
    def send_notification(self, req: dict):
        """
        Handle notification sending request.
        
        Args:
            req: Dictionary containing notification request data
            
        Returns:
            dict: Response with success status and message
            
        Raises:
            HTTPException: If validation fails or processing error occurs
        """
        try:
            # Extract fields from request
            notification_type = req.get("notification_type")
            sender_email = req.get("sender_email")
            box_email = req.get("box_email")
            subject = req.get("subject")
            body = req.get("body")
            timestamp = req.get("timestamp")
            summary_attachment = req.get("summary_attachment")
            overlap = req.get("overlap")
            
            # Validate required fields
            if not notification_type:
                raise ValueError("Notification type is required")
            if not sender_email:
                raise ValueError("Sender email is required")
            if not box_email:
                raise ValueError("Box email is required")
            if not subject:
                raise ValueError("Subject is required")
            if not body:
                raise ValueError("Body is required")
            if not timestamp:
                raise ValueError("Timestamp is required")
            
            # Call service to process notification
            return self.notification_service.send_notification(
                notification_type=notification_type,
                sender_email=sender_email,
                box_email=box_email,
                subject=subject,
                body=body,
                timestamp=timestamp,
                summary_attachment=summary_attachment,
                overlap=overlap
            )
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send notification: {str(e)}"
            )
