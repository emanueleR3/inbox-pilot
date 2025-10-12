from supabase import Client
from fastapi import HTTPException
from supabase_auth.errors import AuthApiError
from api.v1.src.modules.auth.src.models.user_model import UserCrate, UserRead

class UserDAO:
    def __init__(self, supabase: Client):
        #todo: attenzione a questo client
        self.supabase = supabase

    def create_user(self, email: str, password: str):
        response = self.supabase.auth.sign_up({"email": email, "password": password})

        if not response.user:
            raise HTTPException(status_code=400, detail="Errore nella registrazione utente")

        return UserRead(id=response.user.id, email=response.user.email)

    def get_user_by_email(self, email: str):
        result = self.supabase.auth.admin.list_users()

        for u in result.users:
            if u.email == email:
                return UserCrate(id=u.id, email=u.email)
            
        return None
    
    def login_with_password(self, email: str, password: str):
        response = self.supabase.auth.sign_in_with_password({"email": email, "password": password})

        if not response.user:
            raise HTTPException(status_code=401, detail="Credenziali non valide")
        
        return response.session

    def login_with_magic_link(self, email: str):
        response = self.supabase.auth.sign_in_with_otp({"email": email})

        if not response:
            raise HTTPException(status_code=400, detail="Errore durante l'invio del magic link")
        
        return {"message": f"Email di login inviata a {email}"}

    def delete_user(self, user_id: str):
        try:
            response = self.supabase.auth.delete_user(user_id)
            return {"message": f"Utente eliminato"}
        except AuthApiError as e:
            raise HTTPException(status_code=400, detail=str(e))

    def send_password_reset(self, email: str):
        try:
            response = self.supabase.auth.reset_password_email(email)
            return {"message": f"Email di reset inviata a {email}"}
        except AuthApiError as e:
            raise HTTPException(status_code=400, detail=str(e))
