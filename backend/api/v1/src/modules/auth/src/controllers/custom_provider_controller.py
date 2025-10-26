from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse
from src.core.logger import setup_logger
from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO

class CustomProviderController:

    async def custom_provider_login(payload: dict):
        server_imap = payload.get("server_imap")
        server_smtp = payload.get("server_smtp")
        imap_port = payload.get("imap_port")
        smtp_port = payload.get("smtp_port")
        email = payload.get("email")
        password = payload.get("password")
        subscription_id = payload.get("subscription_id")

        missing_fields = []
        if not server_imap:
            missing_fields.append("server_imap")
        if not server_smtp:
            missing_fields.append("server_smtp")
        if not email:
            missing_fields.append("email")
        if not password:
            missing_fields.append("password")
            
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Campi obbligatori mancanti: {', '.join(missing_fields)}"
            )

        if imap_port and not isinstance(imap_port, int):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La porta IMAP deve essere un numero intero"
            )
        if smtp_port and not isinstance(smtp_port, int):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La porta SMTP deve essere un numero intero"
            )

        if not "@" in email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato email non valido"
            )

        try:
            SubscriptionServiceDAO().save_custom_provider_credentials(
                server_imap, server_smtp, imap_port, smtp_port, email, password, subscription_id
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Errore interno durante il salvataggio delle credenziali"
            )

