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

            
            thread_id = req.get("original_thread_id")
            message_id = req.get("message_id")
            attachments = req.get("attachments")  # Optional list of attachments
            
            return self.send_email_service.send_email_gmail(email, subject, body, hashed_access_token, thread_id, message_id, attachments)
            
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

            reply_to_id = req.get("message_id")
            attachments = req.get("attachments")  # Optional list of attachments

            return self.send_email_service.send_email_microsoft(email, subject, body, hashed_access_token, reply_to_id, attachments)
            
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
            password = req.get("password")

            if not email:
                print("[DEBUG-SENDER-CONTROLLER] Email is required")   
                raise ValueError("Email is required")
            if not subject:
                print("[DEBUG-SENDER-CONTROLLER] Subject is required")
                raise ValueError("Subject is required")
            if not body:
                print("[DEBUG-SENDER-CONTROLLER] Body is required")
                raise ValueError("Body is required")
            if not smtp_port:
                print("[DEBUG-SENDER-CONTROLLER] Smtp port is required")
                raise ValueError("Smtp port is required")
            if not smtp_server:
                print("[DEBUG-SENDER-CONTROLLER] Smtp server is required")
                raise ValueError("Smtp server is required")
            if not smtp_email:
                print("[DEBUG-SENDER-CONTROLLER] Smtp email is required")
                raise ValueError("Smtp email is required")
            if not password:
                print("[DEBUG-SENDER-CONTROLLER] Smtp password is required")
                raise ValueError("Smtp password is required")

            reply_to_id = req.get("reply_to_id")
            message_id = req.get("message_id")
            attachments = req.get("attachments")  # Optional list of attachments

            print("[DEBUG-SENDER-CONTROLLER]"+str(req))

            return self.send_email_service.send_email_smtp(
                email, subject, body, smtp_port, smtp_server, smtp_email, password, reply_to_id, message_id, attachments
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send smtp email: {str(e)}"
            )