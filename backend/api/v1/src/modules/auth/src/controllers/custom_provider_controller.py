from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from src.core.logger import setup_logger
from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO

class CustomProviderController:

    async def custom_provider_login(payload: dict):
        try:
            server_imap = payload.get("server_imap")
            server_smtp = payload.get("server_smtp")
            imap_port = payload.get("imap_port")
            smtp_port = payload.get("smtp_port")
            email = payload.get("email")
            password = payload.get("password")
            subscription_id = payload.get("subscription_id")

            # Validazione dei campi richiesti
            if not all([server_imap, server_smtp, email, password]):
                raise HTTPException(
                    status_code=400,
                    detail="Campi obbligatori mancanti: server_imap, server_smtp, email, password"
                )

            result = SubscriptionServiceDAO().save_custom_provider_credentials(
                server_imap, server_smtp, imap_port, smtp_port, email, password, subscription_id
            )

            return {
                "status": "success",
                "message": "Credenziali custom provider salvate con successo",
                "data": result
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Errore interno del server: {str(e)}"
            )

