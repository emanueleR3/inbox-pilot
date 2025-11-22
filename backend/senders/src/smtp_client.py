"""
SMTP client for sending notification emails via Gmail.
Uses App Password authentication which works in containerized environments.
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class SMTPClient:
    """Client for sending emails via SMTP (Gmail with App Password)."""
    
    def __init__(self):
        """Initialize SMTP client with credentials from environment."""
        self.sender_email = os.getenv("SMTP_SENDER_EMAIL", "contact@example.com")
        self.sender_password = os.getenv("SMTP_SENDER_PASSWORD")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        if not self.sender_password:
            logger.warning("⚠️ SMTP_SENDER_PASSWORD not configured - email sending will fail")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send an email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML content of the email
            text_body: Plain text version (optional, will use stripped HTML if not provided)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            if not self.sender_password:
                logger.error("❌ Cannot send email - SMTP_SENDER_PASSWORD not configured")
                return False
            
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = self.sender_email
            message['To'] = to_email
            message['Subject'] = subject
            
            # Add plain text version (for email clients that don't support HTML)
            if text_body:
                text_part = MIMEText(text_body, 'plain', 'utf-8')
                message.attach(text_part)
            
            # Add HTML version
            html_part = MIMEText(html_body, 'html', 'utf-8')
            message.attach(html_part)
            
            # Send email via SMTP
            logger.info(f"📤 Sending email to {to_email} via SMTP...")
            logger.debug(f"🔧 Using SMTP server: {self.smtp_server}:{self.smtp_port}")
            
            # Port 465 requires SSL, port 587 requires STARTTLS
            if self.smtp_port == 465:
                # Use SMTP_SSL for port 465
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(message)
            else:
                # Use SMTP with STARTTLS for port 587
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()  # Upgrade to secure connection
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(message)
            
            logger.info(f"✅ Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP Authentication failed: {e}")
            logger.error("💡 Make sure you're using an App Password, not your regular Gmail password")
            logger.error("💡 Generate App Password at: https://myaccount.google.com/apppasswords")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}", exc_info=True)
            return False


# Global client instance
_smtp_client = None


def get_smtp_client() -> SMTPClient:
    """
    Get or create SMTP client singleton.
    
    Returns:
        SMTPClient instance
    """
    global _smtp_client
    if _smtp_client is None:
        _smtp_client = SMTPClient()
    return _smtp_client
