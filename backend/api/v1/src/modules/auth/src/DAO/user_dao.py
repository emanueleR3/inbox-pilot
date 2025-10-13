from supabase import Client
from fastapi import HTTPException
from supabase_auth.errors import AuthApiError
from api.v1.src.modules.auth.src.models.user_model import UserReadSubscription, UserRead, UserSubscription
from api.v1.src.modules.auth.src.models.subscription_model import SubscriptionRead

class UserDAO:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def create_user(self, email: str, password: str):
        try:
            response = self.supabase.auth.sign_up({"email": email, "password": password})
            if not response.user:
                raise ValueError("Utente non creato da Supabase Auth")
            return UserRead(id=response.user.id, email=response.user.email)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Errore nella registrazione utente: {str(e)}")

    def create_subscription(self, subscription_data: dict):
        try:
            result = self.supabase.table("subscriptions").insert({
                "name": subscription_data.get("name"),
                "vat_number": subscription_data.get("vat_number"),
                "city": subscription_data.get("city"),
                "address": subscription_data.get("address"),
                "active": subscription_data.get("active", False),
                "current_period_end": subscription_data.get("current_period_end").isoformat(),
                "plan": subscription_data.get("plan"),
            }).execute()

            if not result.data:
                raise ValueError("Nessun dato restituito da Supabase dopo l'inserimento")

            sub = result.data[0]
            return SubscriptionRead(**sub)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Errore nella creazione della subscription: {str(e)}")

    def link_user_subscription(self, user_id: str, subscription_id: str):
        try:
            result = self.supabase.table("users_has_subscriptions").insert({
                "user_id": user_id,
                "subscription_id": subscription_id
            }).execute()
            if not result.data:
                raise ValueError("Nessun dato restituito da Supabase dopo l'inserimento della relazione")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Errore nella creazione della relazione user-subscription: {str(e)}")

    def create_user_with_subscription(self, email: str, password: str, subscription_data: dict):
        try:
            user = self.create_user(email, password)
            subscription = self.create_subscription(subscription_data)
            self.link_user_subscription(user.id, subscription.subscription_id)
            return UserReadSubscription(
                id=user.id,
                email=user.email,
                subscription=subscription
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Errore interno durante la creazione utente+subscription: {str(e)}")

    def get_user_by_email(self, email: str):
        users = self.supabase.auth.admin.list_users()

        if not isinstance(users, list):
            users = users.data.get("users", []) if hasattr(users, "data") else []

        for u in users:
            if hasattr(u, "email") and u.email.lower() == email.lower():
                return UserRead(id=u.id, email=u.email)

        raise HTTPException(status_code=404, detail=f"Utente con email {email} non trovato")
    
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
            self.supabase.auth.delete_user(user_id)
            return {"message": f"Utente eliminato"}
        except AuthApiError as e:
            raise HTTPException(status_code=400, detail=str(e))

    def send_password_reset(self, email: str):
        try:
            self.supabase.auth.reset_password_email(email)
            return {"message": f"Email di reset inviata a {email}"}
        except AuthApiError as e:
            raise HTTPException(status_code=400, detail=str(e))

    def update_password(self, new_password: str):
        try:
            self.supabase.auth.update_user({"password": new_password})
            return {"message": f"Password aggiornata correttamente"}
        except AuthApiError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
    def logout(self):
        try:
            self.supabase.auth.sign_out()
            return {"message": f"Logout effettuato con successo"}
        except AuthApiError as e:
            raise HTTPException(status_code=400, detail=str(e))