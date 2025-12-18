from supabase import Client
from fastapi import HTTPException
from src.core.model.subscription import SubscriptionRead, Subscription, SubscriptionUpdate
from src.core.database import get_supabase_client

class SubscriptionDAO:
    def __init__(self):
        self.supabase = get_supabase_client()

    def create_subscription(self, subscription_data: dict):
            sub = Subscription.model_validate(subscription_data)

            sub_dict = sub.model_dump(mode="json")

            result = self.supabase.table("subscriptions").insert(sub_dict).execute()

            if not result.data:
                raise ValueError("Nessun dato restituito da Supabase dopo l'inserimento")

            return SubscriptionRead.model_validate(result.data[0])
    
    def get_subscription_by_id(self, subscription_id: str) -> SubscriptionRead:
        resp = (
            self.supabase
            .table("subscriptions")
            .select("*")
            .eq("subscription_id", subscription_id)
            .execute()
        )

        if not resp.data:
            return None

        return SubscriptionRead(**resp.data[0])
    
    def get_all_subscriptions(self) -> list[SubscriptionRead]:
        """Recupera tutte le sottoscrizioni"""
        resp = self.supabase.table("subscriptions").select("*").execute()
        
        if not resp.data:
            return []
        
        return [SubscriptionRead(**sub) for sub in resp.data]
    
    def update_subscription(self, subscription_id: str, update_data: dict) -> SubscriptionRead:
        """Aggiorna una sottoscrizione esistente"""
        # Valida i dati in arrivo
        update_model = SubscriptionUpdate.model_validate(update_data)
        
        # Converti solo i campi non-None
        update_dict = update_model.model_dump(mode="json", exclude_none=True)
        
        if not update_dict:
            raise ValueError("Nessun campo da aggiornare")
        
        resp = (
            self.supabase
            .table("subscriptions")
            .update(update_dict)
            .eq("subscription_id", subscription_id)
            .execute()
        )
        
        if not resp.data:
            return None
        
        return SubscriptionRead(**resp.data[0])