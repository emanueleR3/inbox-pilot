from supabase import Client
from fastapi import HTTPException
from src.core.model.subscription import SubscriptionRead, Subscription
from src.core.database import get_supabase_client

class SubscriptionDAO:
    def __init__(self):
        self.supabase = get_supabase_client()

    def create_subscription(self, subscription_data: dict):
        try:
            sub = Subscription.model_validate(subscription_data)

            sub_dict = sub.model_dump(mode="json")

            result = self.supabase.table("subscriptions").insert(sub_dict).execute()

            if not result.data:
                raise ValueError("Nessun dato restituito da Supabase dopo l'inserimento")

            return SubscriptionRead.model_validate(result.data[0])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Errore nella creazione della subscription: {str(e)}")