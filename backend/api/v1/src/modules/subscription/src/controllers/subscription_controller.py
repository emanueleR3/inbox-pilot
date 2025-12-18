from src.core.DAO.subscription_dao import SubscriptionDAO
from src.handler_exception import (
    MissingFieldException,
    SubscriptionIdRequiredException,
    BadRequestException,
    NotFoundException,
    APIException,
    DatabaseException
)

class SubscriptionController:
    def __init__(self):
        self.subscription_dao = SubscriptionDAO()
    
    def get_subscription_by_id(self, subscription_id: str):
        """Recupera una sottoscrizione per ID"""
        if not subscription_id:
            raise SubscriptionIdRequiredException()
        
        try:
            subscription = self.subscription_dao.get_subscription_by_id(subscription_id)
            
            if not subscription:
                raise NotFoundException(detail=f"Sottoscrizione con ID {subscription_id} non trovata")
            
            return subscription
        
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"recupero sottoscrizione: {str(e)}")
    
    def get_all_subscriptions(self):
        """Recupera tutte le sottoscrizioni"""
        try:
            subscriptions = self.subscription_dao.get_all_subscriptions()
            return subscriptions
        
        except Exception as e:
            raise DatabaseException(operation=f"recupero sottoscrizioni: {str(e)}")
    
    def create_subscription(self, payload: dict):
        """Crea una nuova sottoscrizione"""
        # Validazione campi obbligatori
        required_fields = ["name", "city", "address", "current_period_end"]
        missing_fields = [field for field in required_fields if not payload.get(field)]
        
        if missing_fields:
            raise MissingFieldException(fields=missing_fields)
        
        try:
            subscription = self.subscription_dao.create_subscription(payload)
            return subscription
        
        except ValueError as e:
            raise BadRequestException(detail=str(e))
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"creazione sottoscrizione: {str(e)}")
    
    def update_subscription(self, subscription_id: str, payload: dict):
        """Aggiorna una sottoscrizione esistente"""
        if not subscription_id:
            raise SubscriptionIdRequiredException()
        
        if not payload:
            raise BadRequestException(detail="Nessun campo da aggiornare")
        
        try:
            # Verifica che la sottoscrizione esista
            existing = self.subscription_dao.get_subscription_by_id(subscription_id)
            if not existing:
                raise NotFoundException(detail=f"Sottoscrizione con ID {subscription_id} non trovata")
            
            # Aggiorna
            updated_subscription = self.subscription_dao.update_subscription(subscription_id, payload)
            
            if not updated_subscription:
                raise DatabaseException(operation="aggiornamento sottoscrizione")
            
            return updated_subscription
        
        except ValueError as e:
            raise BadRequestException(detail=str(e))
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"aggiornamento sottoscrizione: {str(e)}")
