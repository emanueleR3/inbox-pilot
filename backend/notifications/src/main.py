"""
Notifications Service - Main Application
Handles notification webhooks from the automations service.
"""

import os
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
import uvicorn

from .models import NotificationRequest, NotificationResponse, NotificationType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Notifications Service",
    description="Webhook service for handling email notifications from automations",
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "notifications"}


@app.post("/send-notification", response_model=NotificationResponse)
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
        
        # Debug: Print the complete payload
        print("\n" + "="*80)
        print("🔔 NOTIFICATION RECEIVED")
        print("="*80)
        print(f"Type:              {notification.notification_type}")
        print(f"Sender Email:      {notification.sender_email}")
        print(f"Box Email:         {notification.box_email}")
        print(f"Subject:           {notification.subject}")
        print(f"Timestamp:         {notification.timestamp}")
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
        
        # TODO: Implement actual email sending logic here
        # This is where the notification email should be sent
        # For now, we just log and return success
        
        # Generate a unique notification ID (for future tracking)
        notification_id = f"notif_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        logger.info(f"✅ Notification processed successfully - ID: {notification_id}")
        
        return NotificationResponse(
            success=True,
            message="Notification received and queued for processing",
            notification_id=notification_id
        )
        
    except Exception as e:
        logger.error(f"❌ Error processing notification: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process notification: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Notifications Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "send_notification": "/send-notification"
        }
    }


def main():
    """Main entry point for the notifications service."""
    port = int(os.getenv("NOTIFICATIONS_PORT", "8020"))
    host = os.getenv("NOTIFICATIONS_HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting Notifications Service on {host}:{port}")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
