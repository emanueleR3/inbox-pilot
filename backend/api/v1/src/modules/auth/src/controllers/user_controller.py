from fastapi import HTTPException, status
from supabase_auth.errors import AuthApiError
from src.core.DAO.user_dao import UserDAO

class UserController:
    def __init__(self):
        self.user_dao = UserDAO()

    def get_users_by_subscription(self, subscription_id: str):
        if not subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="subscription_id richiesto"
            )

        try:
            users = self.user_dao.get_users_by_subscription(subscription_id)
            
            if not users:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Nessun utente trovato per questa sottoscrizione"
                )

            return users

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore interno durante il recupero degli utenti: {str(e)}"
            )

    def create_user_with_sub(self, payload: dict):
        email = payload.get("email")
        password = payload.get("password")
        subscription_data = payload.get("subscription")

        if not all([email, password, subscription_data]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email e password e i dati della sottoscrizione sono richiesti"
            )
        
        try:
            return self.user_dao.create_user_with_sub(email, password, subscription_data)
        except AuthApiError as e:
            if "User already registered" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Un utente con questa email esiste già"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
        
    def add_new_user(self, payload: dict):
        email = payload.get("email")
        password = payload.get("password")
        subscription_id = payload.get("subscription_id")

        if not all([email, password, subscription_id]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email e password e i dati della sottoscrizione sono richiesti"
            )
        
        try:
            return self.user_dao.add_new_user(email, password, subscription_id)
        except AuthApiError as e:
            if "User already registered" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Un utente con questa email esiste già"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
        
    
    def login_user(self, payload: dict):
        email = payload.get("email")
        password = payload.get("password")

        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email e password sono richiesti"
            )

        try:
            return self.user_dao.login_with_password(email, password)

        except AuthApiError as e:
            msg = str(e)
            if "Invalid login credentials" in msg:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenziali non valide"
                )
            elif "Email not confirmed" in msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email non verificata. Controlla la tua casella email"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Errore interno nel servizio di autenticazione"
                )

    
    def get_user_by_email(self, email: str):
        return self.user_dao.get_user_by_email(email)

    def send_magic_link(self, payload: dict):
        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email richiesta per l'invio del magic link"
            )
            
        try:
            return self.user_dao.login_with_magic_link(email)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except AuthApiError as e:
            if "User not found" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Utente non trovato"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Errore durante l'invio del magic link"
            )

    def delete_account(self, user_id: str):
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID utente richiesto"
            )
            
        try:
            return self.user_dao.delete_user(user_id)
        except AuthApiError as e:
            if "User not found" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Utente non trovato"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Errore durante l'eliminazione dell'account"
            )

    def reset_password(self, payload: dict):
        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email richiesta per il reset della password"
            )

        try:
            return self.user_dao.send_password_reset(email)
        except AuthApiError as e:
            if "User not found" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Utente non trovato"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Errore durante l'invio dell'email di reset"
            )
    
    def update_password(self, payload: dict):
        new_password = payload.get("new_password")
        if not new_password or len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La password deve essere di almeno 6 caratteri"
            )

        try:
            return self.user_dao.update_password(new_password)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except AuthApiError as e:
            if "Auth session missing" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sessione di autenticazione mancante"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Errore durante l'aggiornamento della password"
            )
    
    def logout(self):
        try:
            return self.user_dao.logout()
        except AuthApiError as e:
            if "Auth session missing" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Nessuna sessione attiva da terminare"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Errore durante il logout"
            )
