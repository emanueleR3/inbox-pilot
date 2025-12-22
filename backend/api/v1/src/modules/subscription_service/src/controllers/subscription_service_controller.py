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
    
    def get_service_settings(self, email: str):
        if not email:
            raise MissingFieldException(fields=["email"])
        
        try:
            settings = self.subscription_service_dao.get_service_settings(email)
            if settings is None:
                raise NotFoundException(detail=f"Settings non trovati per email={email}")
            return settings
        
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"recupero service settings: {str(e)}")
    
    def update_service_settings(self, email: str, payload: dict):
        if not email:
            raise MissingFieldException(fields=["email"])
        
        if not payload:
            raise BadRequestException(detail="Nessun dato da aggiornare")
        
        # Validazione campi
        if "business_hours" in payload:
            business_hours = payload["business_hours"]
            if business_hours is not None:
                if not isinstance(business_hours, dict):
                    raise BadRequestException(detail="business_hours deve essere un oggetto JSON")
                
                for day, hours in business_hours.items():
                    if not isinstance(hours, list):
                        raise BadRequestException(detail=f"business_hours[{day}] deve essere un array")
                    for hour_range in hours:
                        if not isinstance(hour_range, str) or "-" not in hour_range:
                            raise BadRequestException(detail=f"Formato orario non valido: {hour_range}. Usare formato HH:MM-HH:MM")
        
        if "appointment_duration" in payload:
            appointment_duration = payload["appointment_duration"]
            if appointment_duration is not None:
                if not isinstance(appointment_duration, int) or appointment_duration <= 0:
                    raise BadRequestException(detail="appointment_duration deve essere un numero intero positivo")
        
        if "email_signature" in payload:
            email_signature = payload["email_signature"]
            if email_signature is not None:
                if not isinstance(email_signature, str):
                    raise BadRequestException(detail="email_signature deve essere una stringa")
        
        if "tone_of_voice" in payload:
            tone_of_voice = payload["tone_of_voice"]
            if tone_of_voice is not None:
                if not isinstance(tone_of_voice, str):
                    raise BadRequestException(detail="tone_of_voice deve essere una stringa")
        
        if "phone_numbers" in payload:
            phone_numbers = payload["phone_numbers"]
            if phone_numbers is not None:
                if not isinstance(phone_numbers, (dict, list)):
                    raise BadRequestException(detail="phone_numbers deve essere un oggetto JSON o un array")
        
        try:
            updated_settings = self.subscription_service_dao.update_service_settings(email, payload)
            if updated_settings is None:
                raise NotFoundException(detail=f"Servizio non trovato per email={email}")
            return updated_settings
        
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"aggiornamento service settings: {str(e)}")
    
    def static_quiz(self, payload: dict) -> dict:
        email = payload.get("email")
        if not email:
            raise MissingFieldException(fields=["email"])
        
        if not isinstance(email, str) or email.strip() == "":
            raise BadRequestException(detail="email deve essere una stringa non vuota")
        
        business_hours = payload.get("business_hours")
        appointment_duration = payload.get("appointment_duration")
        email_signature = payload.get("email_signature")
        tone_of_voice = payload.get("tone_of_voice")
        phone_numbers = payload.get("phone_numbers")
        
        if business_hours is not None:
            if not isinstance(business_hours, dict):
                raise BadRequestException(detail="business_hours deve essere un oggetto JSON")
            
            for day, hours in business_hours.items():
                if not isinstance(hours, list):
                    raise BadRequestException(detail=f"business_hours[{day}] deve essere un array")
                for hour_range in hours:
                    if not isinstance(hour_range, str) or "-" not in hour_range:
                        raise BadRequestException(detail=f"Formato orario non valido: {hour_range}. Usare formato HH:MM-HH:MM")
        
        if appointment_duration is not None:
            if not isinstance(appointment_duration, int) or appointment_duration <= 0:
                raise BadRequestException(detail="appointment_duration deve essere un numero intero positivo")
        
        if email_signature is not None:
            if not isinstance(email_signature, str):
                raise BadRequestException(detail="email_signature deve essere una stringa")
        
        if tone_of_voice is not None:
            if not isinstance(tone_of_voice, str):
                raise BadRequestException(detail="tone_of_voice deve essere una stringa")
        
        if phone_numbers is not None:
            if not isinstance(phone_numbers, (dict, list)):
                raise BadRequestException(detail="phone_numbers deve essere un oggetto JSON o un array")
        
        update_payload = {}
        if business_hours is not None:
            update_payload["business_hours"] = business_hours
        if appointment_duration is not None:
            update_payload["appointment_duration"] = appointment_duration
        if email_signature is not None:
            update_payload["email_signature"] = email_signature
        if tone_of_voice is not None:
            update_payload["tone_of_voice"] = tone_of_voice
        if phone_numbers is not None:
            update_payload["phone_numbers"] = phone_numbers
        
        if not update_payload:
            raise BadRequestException(detail="Nessun campo da aggiornare fornito")
        
        try:
            updated_service = self.subscription_service_dao.static_quiz(email, update_payload)
            
            if not updated_service:
                raise NotFoundException(detail=f"Servizio con email '{email}' non trovato")
            
            return updated_service
        
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"aggiornamento dati static quiz: {str(e)}")