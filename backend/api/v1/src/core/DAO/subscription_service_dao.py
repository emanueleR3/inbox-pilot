from supabase import Client
from fastapi import HTTPException
from supabase_auth.errors import AuthApiError
from datetime import datetime
from src.core.database import get_supabase_client
from src.core.model.subscription_service import SubscriptionServiceCrate, SubscriptionServiceConfigCrate, SubscriptionServiceRead
from pydantic import ValidationError


class SubscriptionServiceDAO:
    def __init__(self):
        self.supabase = get_supabase_client()

    def create_configuration(self, configuration: dict):
        try:
            config = SubscriptionServiceCrate.model_validate(configuration)

            config_dict = config.model_dump(mode="json")

            result = self.supabase.table("subscription_services").insert(config_dict).execute()

            if not result.data:
                raise ValueError("Nessun dato restituito da Supabase dopo l'inserimento")

            return SubscriptionServiceRead.model_validate(result.data[0])

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Errore nella creazione della configurazione: {str(e)}"
            )

    def get_configuration(self, subscription_id: str):
        try:
            result = self.supabase.table("subscription_services").select(
                "subscription_id, confidence_response_threshold, confidence_review_mail, priority_threshold, confidence_classification_threshold, urgent_meeting_threshold"
            ).eq("subscription_id", subscription_id).execute()

            if not result.data:
                return None
            return result.data[0]

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Errore nel recupero: {str(e)}")

    def update_configuration(self, subscription_id: str, updates: dict):
        try:
            config = SubscriptionServiceConfigCrate.model_validate(updates)

            upload_dict = config.model_dump()

            if not upload_dict:
                raise HTTPException(status_code=400, detail="Nessun campo valido da aggiornare")

            result = (
                self.supabase.table("subscription_services")
                .update(upload_dict)
                .eq("subscription_id", subscription_id)
                .execute()
            )

            if not result.data:
                raise HTTPException(status_code=404, detail="Configurazione non trovata")

            return result.data[0]

        except ValidationError as ve:
            raise HTTPException(status_code=422, detail={"validation_error": ve.errors()})
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Errore nell'update: {str(e)}")
        