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
    
    def get_email_signature(self, email: str):
        if not email:
            raise MissingFieldException(fields=["email"])
        
        try:
            email_signature = self.subscription_service_dao.get_email_signature(email)
            if email_signature is None:
                raise NotFoundException(detail=f"Firma email non trovata per email={email}")
            return email_signature
        
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"recupero email_signature: {str(e)}")
    
    def update_email_signature(self, email: str, payload: str):
        if not email:
            raise MissingFieldException(fields=["email"])
        
        if not payload:
            raise BadRequestException(detail="Nessun dato da aggiornare")
        
        if not isinstance(payload, str):
            raise BadRequestException(detail="Email signature deve essere un testo (string)")
        
        if len(payload.strip()) == 0:
            raise BadRequestException(detail="Email signature non può essere una stringa vuota")
        
        try:
            updated_signature = self.subscription_service_dao.update_email_signature(email, payload)
            if updated_signature is None:
                raise NotFoundException(detail=f"Servizio non trovato per email={email}")
            return updated_signature
        
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"aggiornamento email_signature: {str(e)}")
        
    def get_tone_of_voice(self, email: str):
        if not email:
            raise MissingFieldException(fields=["email"])
        
        try:
            tone_of_voice = self.subscription_service_dao.get_tone_of_voice(email)
            if tone_of_voice is None:
                raise NotFoundException(detail=f"Tone-of-voice non trovato per email={email}")
            return tone_of_voice
        
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"recupero tone_of_voice: {str(e)}")
        
    def update_tone_of_voice(self, email: str, payload: str):
        if not email:
            raise MissingFieldException(fields=["email"])
        
        if not payload:
            raise BadRequestException(detail="Nessun dato da aggiornare")
        
        if not isinstance(payload, str):
            raise BadRequestException(detail="Tone-of-voice deve essere un testo (string)")
        
        if len(payload.strip()) == 0:
            raise BadRequestException(detail="Tone-of-voice non può essere una stringa vuota")
        
        try:
            updated_tone = self.subscription_service_dao.update_tone_of_voice(email, payload)
            if updated_tone is None:
                raise NotFoundException(detail=f"Servizio non trovato per email={email}")
            return updated_tone
        
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"aggiornamento tone_of_voice: {str(e)}")
    
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