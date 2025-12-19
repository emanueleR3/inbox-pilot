from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO
from src.handler_exception import (
    MissingFieldException,
    SubscriptionIdRequiredException,
    BadRequestException,
    NotFoundException,
    APIException,
    DatabaseException
)

class SubscriptionServiceController:
    def __init__(self):
        self.subscription_service_dao = SubscriptionServiceDAO()

    def get_configuration(self, subscription_id: str):
        if not subscription_id:
            raise SubscriptionIdRequiredException()

        try:
            result = self.subscription_service_dao.get_configuration(subscription_id)
            if not result:
                raise NotFoundException(detail=f"Configurazione con ID {subscription_id} non trovata")
            return result
        except Exception as e:
            raise DatabaseException(operation=f"recupero configurazione: {str(e)}") 

    def update_configuration(self, subscription_id: str, updates: dict):
        if not subscription_id:
            raise SubscriptionIdRequiredException()

        if not updates:
            raise MissingFieldException(fields=["updates"])

        try:
            result = self.subscription_service_dao.update_configuration(subscription_id, updates)
            if not result:
                raise NotFoundException(detail=f"Configurazione con ID {subscription_id} non trovata")
            return result
        except Exception as e:
            raise DatabaseException(operation=f"aggiornamento configurazione: {str(e)}")
        
    def get_services_by_subscription(self, subscription_id: str, email: str):
     
        if not subscription_id or not email:
            raise MissingFieldException(fields=["subscription_id", "email"])
        
        try:
            services = self.subscription_service_dao.get_services_by_subscription(subscription_id, email)
            if not services:
                    raise NotFoundException(detail="Nessun servizio trovato per questa sottoscrizione e email")
            return services
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"recupero servizi: {str(e)}")
        
    def setup_calendar_information(self, payload: dict) -> bool:
        email = payload.get("email")
        business_hours = payload.get("business_hours")
        appointment_duration = payload.get("appointment_duration")

        if business_hours is None or appointment_duration is None:
            raise MissingFieldException(fields=["business_hours", "appointment_duration"])

        if not isinstance(business_hours, dict) or not business_hours:
            raise BadRequestException(detail="business_hours deve essere un oggetto non vuoto")

        if not isinstance(appointment_duration, int) or appointment_duration <= 0:
            raise BadRequestException(detail="appointment_duration deve essere un intero positivo")

        if not email:
            raise SubscriptionIdRequiredException()

        try:
            updated = self.subscription_service_dao.setup_calendar_information(
                email=email,
                business_hours=business_hours,
                appointment_duration=appointment_duration,
            )
            if not updated:
                raise NotFoundException(detail="Nessun servizio trovato per salvare le informazioni calendario")
            return True

        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"setup informazioni calendario: {str(e)}")
        
    def get_calendar_information(self, payload: dict):
        email = payload.get("email")

        if not email:
            raise MissingFieldException(fields=["email"])

        try:
            information = self.subscription_service_dao.get_calendar_information(email)
            if information is None:
                raise NotFoundException(detail=f"Informazioni calendario non trovate per email={email}")
            return information

        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"recupero informazioni calendario: {str(e)}")
    
    def get_information(self, email: str):
        if not email:
            raise MissingFieldException(fields=["email"])
        
        try:
            information = self.subscription_service_dao.get_information(email)
            if information is None:
                raise NotFoundException(detail=f"Informazioni non trovate per email={email}")
            return information
        
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"recupero information: {str(e)}")
    
    def update_information(self, email: str, payload: str):
        """Aggiorna il campo information per un servizio"""
        if not email:
            raise MissingFieldException(fields=["email"])
        
        if not payload:
            raise BadRequestException(detail="Nessun dato da aggiornare")
        
        if not isinstance(payload, str):
            raise BadRequestException(detail="Information deve essere un testo (string)")
        
        if len(payload.strip()) == 0:
            raise BadRequestException(detail="Information non può essere una stringa vuota")
        
        try:
            updated_info = self.subscription_service_dao.update_information(email, payload)
            if updated_info is None:
                raise NotFoundException(detail=f"Servizio non trovato per email={email}")
            return updated_info
        
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"aggiornamento information: {str(e)}")