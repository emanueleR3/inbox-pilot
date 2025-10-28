from fastapi import HTTPException, status
from supabase_auth.errors import AuthApiError
from src.core.model.user import UserRead, UserReadSub
from src.core.redis_client import get_redis_client
#from src.core.model.subscription_service import SubscriptionServiceCrate
from src.core.DAO.subscription_dao import SubscriptionDAO
#from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO
from src.core.database import get_supabase_client, get_fresh_supabase_client
import time

class UserDAO:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.supabase_auth = get_fresh_supabase_client() 

    def login_with_password(self, email: str, password: str):
        try:
            response = self.supabase_auth.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            return response.session
        
        except AuthApiError as e:
            raise e
    
    def create_user(self, email: str, password: str):
        try:

            response = self.supabase_auth.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                }
            )

            return UserRead(id=response.user.id, email=response.user.email)
        except Exception as e:
            raise e

    def link_user_subscription(self, user_id: str, subscription_id: str):
        try:
            self.supabase.table("users_has_subscriptions").insert({
                "user_id": user_id,
                "subscription_id": subscription_id
            }).execute()
        except Exception as e:
            raise e

    def create_user_with_sub(self, email: str, password: str, subscription_data: dict):
        try:
            subscription = SubscriptionDAO().create_subscription(subscription_data)
            user = self.create_user(email, password)

            self.link_user_subscription(user.id, subscription.subscription_id)

            response = self.login_with_password(email, password)

            return UserReadSub.model_construct(
                id=user.id,
                email=user.email,
                subscription=subscription,
                jwt= response.access_token
            )
        except Exception as e:
            raise e

    def get_user_by_email(self, email: str):
        # 1) Try Redis cache first
        r = get_redis_client()
        cache_key = f"user:by_email:{email.lower()}"
        cached = r.hgetall(cache_key)
        if cached and cached.get("id") and cached.get("email"):
            return UserRead(id=cached["id"], email=cached["email"])

        # 2) Fallback to Supabase search
        users = self.supabase.auth.admin.list_users()

        if not isinstance(users, list):
            users = users.data.get("users", []) if hasattr(users, "data") else []

        for u in users:
            if hasattr(u, "email") and u.email and u.email.lower() == email.lower():
                # Cache user info with a TTL
                try:
                    r.hset(cache_key, mapping={"id": u.id, "email": u.email})
                    r.expire(cache_key, 1200)  # 20 minutes
                except Exception:
                    pass # Cache failures shouldn't block main flow
                return UserRead(id=u.id, email=u.email)

        raise HTTPException(status_code=404, detail=f"Utente con email {email} non trovato")
    
    def get_subscriptions_by_user(self, user_id: str, access_token):
        try:
            
            self.supabase.postgrest.auth(access_token)

            response = (
                self.supabase
                .table("users_has_subscriptions")
                .select("subscription_id")
                .eq("user_id", user_id)
                .execute()
            )
            return [item["subscription_id"] for item in response.data]
        except Exception as e:
            raise e
        
    def get_user_by_subscription(self, subscription_id: str):
        try:
            response = (
                self.supabase
                .table("users_has_subscriptions")
                .select("user_id")
                .eq("subscription_id", subscription_id)
                .execute()
            )

            return [item["user_id"] for item in response.data]
        except Exception as e:
            raise e
    
    def login_with_magic_link(self, email: str):
        response = self.supabase.auth.sign_in_with_otp({
            "email": email, 
            "options": {"redirect_to":  "https://corretto.pro/dashboard"}
        })
        return response.session

    def logout(self):
        try:
            return self.supabase_auth.auth.sign_out()
           
        except AuthApiError as e:
            raise e
        except Exception as e:
            raise e
    

