from fastapi import HTTPException, status
from supabase_auth.errors import AuthApiError
from src.core.model.user import UserRead, UserReadSub, UserReadSubs
from src.core.model.subscription import SubscriptionRead, SubscriptionReadWithConfig
from src.core.redis_client import get_redis_client
from src.core.DAO.subscription_dao import SubscriptionDAO
from src.core.database import get_supabase_client, get_fresh_supabase_client
import time

class UserDAO:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.supabase_auth = get_fresh_supabase_client() 

    def get_users_by_subscription(self, subscription_id: str) -> list[UserRead]:
            link_response = (
                self.supabase
                    .table("users_has_subscriptions")
                    .select("user_id")
                    .eq("subscription_id", subscription_id)
                    .execute()
            )

            if not link_response.data:
                return []

            user_ids = [row["user_id"] for row in link_response.data]

            users_response = self.supabase.auth.admin.list_users()

            if isinstance(users_response, list):
                users = users_response

            if not users:
                return []

            result = []
            for u in users:
                if getattr(u, "id", None) in user_ids:
                    result.append(UserRead(id=u.id, email=u.email))

            return result

    def get_subscriptions_by_user(self, user_id: str) -> list[SubscriptionReadWithConfig]:
        link_response = (
            self.supabase
            .table("users_has_subscriptions")
            .select("subscription_id")
            .eq("user_id", user_id)
            .execute()
        )

        if not link_response.data:
            return []

        subscription_ids = [row["subscription_id"] for row in link_response.data]

        subs_response = (
            self.supabase
            .table("subscriptions")
            .select("subscription_id, name, vat_number, city, address, active, current_period_end, plan")
            .in_("subscription_id", subscription_ids)
            .execute()
        )

        if not subs_response.data:
            return []

        config_response = (
            self.supabase
            .table("subscription_services")
            .select("subscription_id, config_completed")
            .in_("subscription_id", subscription_ids)
            .execute()
        )

        config_map = {
            c["subscription_id"]: c.get("config_completed", False)
            for c in (config_response.data or [])
        }

        subscriptions = [
            SubscriptionReadWithConfig(
                subscription_id=sub["subscription_id"],
                name=sub["name"],
                vat_number=sub.get("vat_number"),
                city=sub["city"],
                address=sub["address"],
                active=sub["active"],
                current_period_end=sub["current_period_end"],
                plan=sub.get("plan"),
                is_configurated=config_map.get(sub["subscription_id"], False),
            )
            for sub in subs_response.data
        ]

        return subscriptions


    def login_with_password(self, email: str, password: str) -> UserReadSubs:
        response = self.supabase_auth.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        subscriptions = self.get_subscriptions_by_user(response.session.user.id)

        return UserReadSubs(
            id = response.session.user.id,
            email = response.session.user.email,
            subscriptions=subscriptions,
            jwt=response.session.access_token,
            sub_selected=0
        )
    
    def create_user(self, email: str, password: str) -> UserRead:
        response = self.supabase_auth.auth.sign_up(
            {
                "email": email,
                "password": password,
            }
        )

        return UserRead(id=response.user.id, email=response.user.email)      

    def link_user_subscription(self, user_id: str, subscription_id: str) -> bool:
        self.supabase.table("users_has_subscriptions").insert({
            "user_id": user_id,
            "subscription_id": subscription_id
        }).execute()

        return True
    
    def create_user_with_sub(self, email: str, password: str, subscription_data: dict) -> UserReadSubs:
        user = self.create_user(email, password)

        self.supabase_auth.rpc(
            "create_subscription_for_user",
            {
                "p_user_id": user.id,
                "p_subscription": subscription_data
            }
        ).execute()

        response = self.login_with_password(email, password)

        return response
   
    def add_new_user(self, email: str, password: str, subscription_id: str) -> bool:
        user = self.create_user(email, password)

        response = self.supabase.rpc(
            "add_new_user",
            {
                "p_user_id": user.id,
                "p_subscription_id": subscription_id
            }
        ).execute()

        return response

    def create_new_sub(self, user: dict, subscription_data: dict) -> UserReadSubs:
        # Estrai i campi dal dict utente
        user_id = user.get("id")
        user_email = user.get("email")
        user_subscriptions = user.get("subscriptions", [])
        user_jwt = user.get("jwt")
        user_sub_selected = user.get("sub_selected")

        # Crea una nuova subscription
        subscription = SubscriptionDAO().create_subscription(subscription_data)

        # Collega l’utente alla subscription
        self.link_user_subscription(user_id, subscription.subscription_id)

        # Aggiungi la nuova subscription all’elenco
        user_subscriptions.append(subscription)

        # Recupera l’indice dell’ultima subscription
        last_index = len(user_subscriptions) - 1

        # Ritorna il nuovo oggetto UserReadSubs
        return UserReadSubs(
            id=user_id,
            email=user_email,
            subscriptions=user_subscriptions,
            jwt=user_jwt,
            sub_selected=last_index  # 🔥 deve essere un int, non un oggetto
        )



    def get_user_by_email(self, email: str):
        try:
            # 1) Try Redis cache first
            r = get_redis_client()
            cache_key = f"user:by_email:{email.lower()}"
            cached = r.hgetall(cache_key)
            if cached and cached.get("id") and cached.get("email"):
                return UserRead(id=cached["id"], email=cached["email"])
        except Exception:
            # If Redis fails, continue to Supabase lookup
            pass

        # 2) Fallback to Supabase search
        try:
            users = self.supabase.auth.admin.list_users()

            if not isinstance(users, list):
                users = users.data.get("users", []) if hasattr(users, "data") else []

            for u in users:
                if hasattr(u, "email") and u.email and u.email.lower() == email.lower():
                    # Cache user info with a TTL
                    try:
                        r = get_redis_client()
                        cache_key = f"user:by_email:{email.lower()}"
                        r.hset(cache_key, mapping={"id": u.id, "email": u.email})
                        r.expire(cache_key, 1200)  # 20 minutes
                    except Exception:
                        pass # Cache failures shouldn't block main flow
                    return UserRead(id=u.id, email=u.email)

            raise HTTPException(status_code=404, detail=f"Utente con email {email} non trovato")
        
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante la ricerca dell'utente: {str(e)}"
            )
    
    def login_with_magic_link(self, email: str):
        response = self.supabase.auth.sign_in_with_otp({
            "email": email, 
            "options": {"redirect_to":  "https://corretto.pro/dashboard"}
        })
        return response.session

    def logout(self):
        return self.supabase_auth.auth.sign_out()
    

