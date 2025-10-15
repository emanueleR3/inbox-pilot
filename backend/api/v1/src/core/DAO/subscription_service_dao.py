from supabase import Client
from fastapi import HTTPException
from supabase_auth.errors import AuthApiError
from datetime import datetime
from src.core.database import get_supabase_client

class SubscriptionServiceDAO:
    def __init__(self):
        self.supabase = get_supabase_client()

    def create_configuration(self, configuration: dict):
        try:
            result = self.supabase.table("subscription_services").insert({
                "email": configuration.get("email"),
                "subscription_id": configuration.get("subscription_id"),
                "calendar_provider": configuration.get("calendar_provider"),
                "calendar_names": configuration.get("calendar_names"),
                "information": configuration.get("information"),
                "imap_server": configuration.get("imap_server"),
                "imap_port": configuration.get("imap_port"),
                "smtp_server": configuration.get("smtp_server"),
                "smtp_port": configuration.get("smtp_port"),
                "hashed_password": configuration.get("hashed_password"),
                "hashed_access_token": configuration.get("hashed_access_token"),
                "hashed_refresh_token": configuration.get("hashed_refresh_token"),
                "expiry_token": configuration.get("expiry_token").isoformat()
                    if isinstance(configuration.get("expiry_token"), datetime)
                    else configuration.get("expiry_token"),
                "confidence_response_threshold": configuration.get("confidence_response_threshold"),
                "confidence_review_mail": configuration.get("confidence_review_mail"),
                "priority_threshold": configuration.get("priority_threshold"),
                "confidence_classification_threshold": configuration.get("confidence_classification_threshold"),
                "urgent_meeting_threshold": configuration.get("urgent_meeting_threshold"),
                "history_id": configuration.get("history_id"),
                "microsoft_subscription_id": configuration.get("microsoft_subscription_id"),
                "microsoft_expiration_datetime": configuration.get("microsoft_expiration_datetime").isoformat()
                    if isinstance(configuration.get("microsoft_expiration_datetime"), datetime)
                    else configuration.get("microsoft_expiration_datetime"),
                "oauth_user_id": configuration.get("oauth_user_id"),
            }).execute()

            if not result.data:
                raise ValueError("Nessun dato restituito da Supabase dopo l'inserimento")

            new_config = result.data[0]
            return new_config

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Errore nella creazione della configurazione: {str(e)}"
            )
        