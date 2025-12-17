from supabase_auth.errors import AuthApiError
from src.core.DAO.user_dao import UserDAO
from src.core.DAO.subscription_dao import SubscriptionDAO
from src.handler_exception import (
    SubscriptionIdRequiredException,
    MissingFieldException,
    NotFoundException,
    UserNotFoundException,
    SubscriptionNotFoundException,
    ResourceAlreadyExistsException,
    InvalidCredentialsException,
    BadRequestException,
    UnauthorizedException,
    DatabaseException,
    APIException
)


class UserController:
    def __init__(self):
        self.user_dao = UserDAO()
        self.subscription_dao = SubscriptionDAO()

    def setup_calendar_information(self, payload: dict) -> bool:
        subscription_id = payload.get("subscription_id")
        business_hours = payload.get("business_hours")
        appointment_duration = payload.get("appointment_duration")

        if business_hours is None or appointment_duration is None:
            raise MissingFieldException(fields=["business_hours", "appointment_duration"])

        if not isinstance(business_hours, dict) or not business_hours:
            raise BadRequestException(detail="business_hours deve essere un oggetto non vuoto")

        if not isinstance(appointment_duration, int) or appointment_duration <= 0:
            raise BadRequestException(detail="appointment_duration deve essere un intero positivo")

        if not subscription_id:
            raise SubscriptionIdRequiredException()

        try:
            updated = self.subscription_dao.setup_calendar_information(
                subscription_id=subscription_id,
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

    def get_users_by_subscription(self, subscription_id: str):
        if not subscription_id:
            raise SubscriptionIdRequiredException()

        try:
            users = self.user_dao.get_users_by_subscription(subscription_id)
            
            if not users:
                raise NotFoundException(detail="Nessun utente trovato per questa sottoscrizione")

            return users

        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"recupero utenti: {str(e)}")

    def create_user_with_sub(self, payload: dict):
        email = payload.get("email")
        password = payload.get("password")
        subscription_data = payload.get("subscription")

        if not all([email, password, subscription_data]):
            raise MissingFieldException(fields=["email", "password", "subscription"])
        
        try:
            return self.user_dao.create_user_with_sub(email, password, subscription_data)
        except AuthApiError as e:
            if "User already registered" in str(e):
                raise ResourceAlreadyExistsException(resource="Utente con questa email")
            raise DatabaseException(operation=str(e))
        
    def add_new_user(self, payload: dict):
        email = payload.get("email")
        password = payload.get("password")
        subscription_id = payload.get("subscription_id")

        if not all([email, password, subscription_id]):
            raise MissingFieldException(fields=["email", "password", "subscription_id"])
        
        try:
            return self.user_dao.add_new_user(email, password, subscription_id)
        except AuthApiError as e:
            if "User already registered" in str(e):
                raise ResourceAlreadyExistsException(resource="Utente con questa email")
            raise DatabaseException(operation=str(e))
        
    def create_new_sub(self, payload: dict):
        user = payload.get("user")
        subscription_data = payload.get("subscription")

        if not all([user, subscription_data]):
            raise MissingFieldException(fields=["user", "subscription"])
        
        try:
            return self.user_dao.create_new_sub(user, subscription_data)
        except AuthApiError as e:
            if "Subs already created" in str(e):
                raise ResourceAlreadyExistsException(resource="Sottoscrizione")
            raise DatabaseException(operation=str(e))
        
    
    def login_user(self, payload: dict):
        email = payload.get("email")
        password = payload.get("password")

        if not email or not password:
            raise MissingFieldException(fields=["email", "password"])

        try:
            return self.user_dao.login_with_password(email, password)

        except AuthApiError as e:
            msg = str(e)
            if "Invalid login credentials" in msg:
                raise InvalidCredentialsException()
            elif "Email not confirmed" in msg:
                raise BadRequestException(detail="Email non verificata. Controlla la tua casella email")
            else:
                raise DatabaseException(operation="autenticazione")

    
    def get_user_by_email(self, email: str):
        return self.user_dao.get_user_by_email(email)

    def send_magic_link(self, payload: dict):
        email = payload.get("email")
        if not email:
            raise MissingFieldException(fields=["email"])
            
        try:
            return self.user_dao.login_with_magic_link(email)
        except ValueError as e:
            raise BadRequestException(detail=str(e))
        except AuthApiError as e:
            if "User not found" in str(e):
                raise UserNotFoundException()
            raise DatabaseException(operation="invio magic link")

    def delete_account(self, user_id: str):
        if not user_id:
            raise MissingFieldException(fields=["user_id"])
            
        try:
            return self.user_dao.delete_user(user_id)
        except AuthApiError as e:
            if "User not found" in str(e):
                raise UserNotFoundException()
            raise DatabaseException(operation="eliminazione account")

    def reset_password(self, payload: dict):
        email = payload.get("email")
        if not email:
            raise MissingFieldException(fields=["email"])

        try:
            return self.user_dao.send_password_reset(email)
        except AuthApiError as e:
            if "User not found" in str(e):
                raise UserNotFoundException()
            raise DatabaseException(operation="invio email di reset")
    
    def update_password(self, payload: dict):
        new_password = payload.get("new_password")
        if not new_password or len(new_password) < 6:
            raise BadRequestException(detail="La password deve essere di almeno 6 caratteri")

        try:
            return self.user_dao.update_password(new_password)
        except ValueError as e:
            raise BadRequestException(detail=str(e))
        except AuthApiError as e:
            if "Auth session missing" in str(e):
                raise UnauthorizedException(detail="Sessione di autenticazione mancante")
            raise DatabaseException(operation="aggiornamento password")
    
    def logout(self):
        try:
            return self.user_dao.logout()
        except AuthApiError as e:
            if "Auth session missing" in str(e):
                raise UnauthorizedException(detail="Nessuna sessione attiva da terminare")
            raise DatabaseException(operation="logout")
    
    def get_subscription_by_id(self, subscription_id: str):
        if not subscription_id:
            raise SubscriptionIdRequiredException()

        try:
            sub = self.subscription_dao.get_subscription_by_id(subscription_id)
            if not sub:
                raise SubscriptionNotFoundException(subscription_id=subscription_id)
            return sub
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"recupero sottoscrizione: {str(e)}")
