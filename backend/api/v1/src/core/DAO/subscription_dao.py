from supabase import Client
from fastapi import HTTPException
from src.core.model.subscription import SubscriptionRead
from src.core.database import get_supabase_client

class SubscriptionDAO:
    def __init__(self):
        self.supabase = get_supabase_client()

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