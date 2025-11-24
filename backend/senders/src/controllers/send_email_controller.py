from fastapi import HTTPException, status
from supabase_auth.errors import AuthApiError
from src.services.send_email_service import SendEmailService

class SendEmailController:
    def __init__(self):
        self.send_email_service = SendEmailService()
    
    def send_email_gmail(self, req: dict):
        try:
            email = req.get("email")
            subject = req.get("subject")
            body = req.get("body")
            hashed_access_token = req.get("hashed_access_token")

            if not email:
                raise ValueError("Email is required")
            if not subject:
                raise ValueError("Subject is required")
            if not body:
                raise ValueError("Body is required")
            if not hashed_access_token:
                raise ValueError("Hashed access token is required")

            
            return self.send_email_service.send_email_gmail(email, subject, body, hashed_access_token)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send gmail email: {str(e)}"
            )
        
    def send_email_microsoft(self, req: dict):
        try:
            email = req.get("email")
            subject = req.get("subject")
            body = req.get("body")
            hashed_access_token = req.get("hashed_access_token")

            if not email:
                raise ValueError("Email is required")
            if not subject:
                raise ValueError("Subject is required")
            if not body:
                raise ValueError("Body is required")
            if not hashed_access_token:
                raise ValueError("Hashed access token is required")

            return self.send_email_service.send_email_microsoft(email, subject, body, hashed_access_token)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send microsoft email: {str(e)}"
            )
        
    def send_email_smtp(self, req: dict):
        try:
            email = req.get("email")
            subject = req.get("subject")
            body = req.get("body")
            smtp_port = req.get("smtp_port")
            smtp_server = req.get("smtp_server")
            smtp_email = req.get("smtp_email")
            smtp_password = req.get("smtp_password")

            if not email:   
                raise ValueError("Email is required")
            if not subject:
                raise ValueError("Subject is required")
            if not body:
                raise ValueError("Body is required")
            if not smtp_port:
                raise ValueError("Smtp port is required")
            if not smtp_server:
                raise ValueError("Smtp server is required")
            if not smtp_email:
                raise ValueError("Smtp email is required")
            if not smtp_password:
                raise ValueError("Smtp password is required")

            return self.send_email_service.send_email_smtp(email, subject, body, smtp_port, smtp_server, smtp_email, smtp_password)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send smtp email: {str(e)}"
            )