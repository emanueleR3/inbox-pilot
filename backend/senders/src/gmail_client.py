"""
Gmail API client for sending notification emails.
"""

import os
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class GmailClient:
    """Client for sending emails via Gmail API."""
    
    def __init__(self):
        """Initialize Gmail client with credentials."""
        self.sender_email = os.getenv("GMAIL_SENDER_EMAIL", "contact@example.com")
        self.credentials_file = os.getenv("GMAIL_CREDENTIALS_FILE")
        self.token_file = os.getenv("GMAIL_TOKEN_FILE")
        self.service = None
        
    def _get_credentials(self) -> Optional[Credentials]:
        """
        Get valid user credentials from storage or generate new ones.
        
        Returns:
            Valid credentials or None if authentication fails
        """
        creds = None
        
        # Try to load existing token
        if self.token_file and os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                logger.info("✅ Loaded existing Gmail credentials from token file")
            except Exception as e:
                logger.warning(f"⚠️ Could not load token file: {e}")
        
        # If credentials are invalid or don't exist, refresh or create new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("🔄 Refreshing expired Gmail credentials...")
                    creds.refresh(Request())
                    logger.info("✅ Gmail credentials refreshed successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to refresh credentials: {e}")
                    creds = None
            
            # If refresh failed or no credentials, need new authentication
            if not creds:
                if not self.credentials_file or not os.path.exists(self.credentials_file):
                    logger.error("❌ Gmail credentials file not found. Please provide GMAIL_CREDENTIALS_FILE")
                    return None
                
                try:
                    logger.info("🔐 Starting new Gmail OAuth flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    # Use local server for OAuth flow
                    creds = flow.run_local_server(port=0)
                    logger.info("✅ Gmail authentication successful")
                except Exception as e:
                    logger.error(f"❌ Failed to authenticate: {e}")
                    return None
            
            # Save credentials for future use
            if creds and self.token_file:
                try:
                    # Ensure directory exists
                    token_dir = os.path.dirname(self.token_file)
                    if token_dir:
                        os.makedirs(token_dir, exist_ok=True)
                    
                    with open(self.token_file, 'w') as token:
                        token.write(creds.to_json())
                    logger.info(f"💾 Saved Gmail credentials to {self.token_file}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not save token file: {e}")
        
        return creds
    
    def _initialize_service(self) -> bool:
        """
        Initialize Gmail API service.
        
        Returns:
            True if service initialized successfully, False otherwise
        """
        if self.service:
            return True
        
        try:
            creds = self._get_credentials()
            if not creds:
                logger.error("❌ No valid credentials available")
                return False
            
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("✅ Gmail API service initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gmail service: {e}")
            return False
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send an email via Gmail API.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML content of the email
            text_body: Plain text version (optional, will use stripped HTML if not provided)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Initialize service if needed
            if not self._initialize_service():
                logger.error("❌ Cannot send email - Gmail service not initialized")
                return False
            
            # Create message
            message = MIMEMultipart('alternative')
            message['To'] = to_email
            message['From'] = self.sender_email
            message['Subject'] = subject
            
            # Add plain text version (for email clients that don't support HTML)
            if text_body:
                text_part = MIMEText(text_body, 'plain', 'utf-8')
                message.attach(text_part)
            
            # Add HTML version
            html_part = MIMEText(html_body, 'html', 'utf-8')
            message.attach(html_part)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send email
            logger.info(f"📤 Sending email to {to_email}...")
            result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"✅ Email sent successfully - Message ID: {result.get('id')}")
            return True
            
        except HttpError as error:
            logger.error(f"❌ Gmail API error: {error}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}", exc_info=True)
            return False


# Global client instance
_gmail_client = None


def get_gmail_client() -> GmailClient:
    """
    Get or create Gmail client singleton.
    
    Returns:
        GmailClient instance
    """
    global _gmail_client
    if _gmail_client is None:
        _gmail_client = GmailClient()
    return _gmail_client
