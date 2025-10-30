from fastapi import HTTPException, status
from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO


class SubscriptionServiceController:
    def __init__(self):
        self.subscription_service_dao = SubscriptionServiceDAO()

    def get_configuration(self, subscription_id: str):
        if not subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID sottoscrizione richiesto"
            )

        try:
            result = self.subscription_service_dao.get_configuration(subscription_id)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Configurazione con ID {subscription_id} non trovata"
                )
            return result
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Errore durante il recupero della configurazione"
            )

    def update_configuration(self, subscription_id: str, updates: dict):
        if not subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID sottoscrizione richiesto"
            )

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nessun aggiornamento fornito"
            )

        try:
            result = self.subscription_service_dao.update_configuration(subscription_id, updates)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Configurazione con ID {subscription_id} non trovata"
                )
            return result
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Errore durante l'aggiornamento della configurazione"
            )