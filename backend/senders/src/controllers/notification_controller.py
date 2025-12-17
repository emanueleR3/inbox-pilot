from ..services.notification_service import NotificationService
from ..handler_exception import (
    NotificationBodyRequiredException,
    NotificationBoxEmailRequiredException,
    NotificationSendFailedException,
    NotificationSenderEmailRequiredException,
    NotificationSubjectRequiredException,
    NotificationTimestampRequiredException,
    NotificationTypeRequiredException,
)


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
            
            # Validate required fields (check for None, not empty strings)
            if notification_type is None:
                raise NotificationTypeRequiredException()
            if sender_email is None:
                raise NotificationSenderEmailRequiredException()
            if box_email is None:
                raise NotificationBoxEmailRequiredException()
            if subject is None:
                raise NotificationSubjectRequiredException()
            if body is None:
                raise NotificationBodyRequiredException()
            if timestamp is None:
                raise NotificationTimestampRequiredException()
            
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
        except Exception as e:
            raise NotificationSendFailedException(e)
