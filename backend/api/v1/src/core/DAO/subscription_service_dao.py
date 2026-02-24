from realtime import Optional
from src.core.database import get_supabase_client
from src.core.utils.utils import encrypt_token, decrypt_token
from cryptography.fernet import Fernet
import base64
import hashlib
import os
import logging
from dotenv import load_dotenv
from src.core.model.subscription_service import OAuthGoogleCredentials, SubscriptionServiceCrate, SubscriptionServiceConfigCrate, SubscriptionServiceRead
from datetime import datetime, timedelta, timezone
from typing import List

load_dotenv()

class SubscriptionServiceDAO:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    def save_custom_provider_credentials(
        self,
        server_imap: str,
        server_smtp: str,
        imap_port: int,
        smtp_port: int,
        email: str,
        password: str,
        subscription_id: str,
        calendar_provider: str,
        service_id: str
    ) -> SubscriptionServiceRead:
        try:
            encrypted_password = encrypt_token(password, "pass")

            # service_id è obbligatorio
            if not service_id:
                logging.error("service_id mancante per save_custom_provider_credentials")
                raise ValueError("service_id è obbligatorio. Devi prima creare un service con create-new-service e passare il service_id")

            data = {
                "email_provider": "imap",
                "imap_server": server_imap,
                "smtp_server": server_smtp,
                "imap_port": imap_port,
                "smtp_port": smtp_port,
                "hashed_password": encrypted_password,
                "hashed_access_token": None,
                "hashed_refresh_token": None,
                "expiry_token": None,
                "calendar_provider": calendar_provider
            }

            # Verifica che il service_id esista con subscription_id corretto
            check_response = (
                self.supabase.table("subscription_services")
                .select("service_id")
                .eq("service_id", service_id)
                .eq("subscription_id", subscription_id)
                .execute()
            )
            
            if not check_response.data:
                logging.error(f"Service non trovato: service_id={service_id}, subscription_id={subscription_id}")
                raise ValueError(f"Service non trovato. Devi prima creare un service con create-new-service")
            
            # Se esiste, aggiorna
            data["email"] = email
            response = (
                self.supabase.table("subscription_services")
                .update(data)
                .eq("service_id", service_id)
                .execute()
            )

            if not response.data:
                logging.warning(f"Errore nell'aggiornamento del service_id: {service_id}")
                raise ValueError(f"Errore nell'aggiornamento del service")
            
            record = response.data[0]

            return SubscriptionServiceRead(
                email=record.get("email"),
                subscription_id=record.get("subscription_id"),
                email_provider=record.get("email_provider"),
                imap_server=record.get("imap_server"),
                imap_port=record.get("imap_port"),
                smtp_server=record.get("smtp_server"),
                smtp_port = record.get("smtp_port"),
                confidence_response_threshold = record.get("confidence_response_threshold"),
                confidence_review_mail = record.get("confidence_review_mail"),
                priority_threshold=record.get("priority_threshold"),
                confidence_classification_threshold = record.get("confidence_classification_threshold"),
                urgent_meeting_threshold = record.get("urgent_meeting_threshold"),
                calendar_provider = record.get("calendar_provider")
            )

        except Exception as e:
            logging.exception(f"Errore nel salvataggio delle credenziali per {email}: {e}")
            raise



    def save_microsoft_credentials(
        self, 
        email: str, 
        subscription_id: str, 
        access_token: str, 
        refresh_token: str, 
        expiry,
        microsoft_subscription_id_inbound: str = None,
        microsoft_subscription_id_outbound: str = None,
        microsoft_expiration_datetime_inbound = None,
        microsoft_expiration_datetime_outbound = None,
        service_id: str = None
    ) -> bool:
        """
        Salva le credenziali Microsoft nel database per l'utente con l'email specificata.
        I token vengono cifrati prima del salvataggio.
        
        Args:
            email: Email dell'utente
            subscription_id: ID della subscription
            access_token: Token di accesso Microsoft
            refresh_token: Token di refresh Microsoft
            expiry: Data di scadenza del token (secondi o datetime)
            microsoft_subscription_id_inbound: ID della subscription Microsoft Graph per email in entrata
            microsoft_subscription_id_outbound: ID della subscription Microsoft Graph per email in uscita
            microsoft_expiration_datetime_inbound: Data di scadenza della subscription Graph inbound
            microsoft_expiration_datetime_outbound: Data di scadenza della subscription Graph outbound
            service_id: ID del service esistente da aggiornare (OBBLIGATORIO)
        """
        try:
            # service_id è obbligatorio
            if not service_id:
                logging.error("service_id mancante per save_microsoft_credentials")
                raise ValueError("service_id è obbligatorio. Devi prima creare un service con create-new-service e passare il service_id")

            # Cifra i token prima del salvataggio
            encrypted_access_token = encrypt_token(access_token, "token")
            encrypted_refresh_token = encrypt_token(refresh_token, "token")

            # Converti expiry (expires_in in secondi) in oggetto datetime
            expiry_datetime = None
            if expiry:
                if isinstance(expiry, (int, float)):
                    now = datetime.now(timezone.utc)
                    expiry_datetime = now + timedelta(seconds=expiry)
                    logging.info(f"Microsoft token expiry calculation: now={now.isoformat()}, expires_in={expiry}s, expiry={expiry_datetime.isoformat()}")
                elif isinstance(expiry, str):
                    expiry_datetime = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                    logging.info(f"Microsoft token expiry from ISO string: {expiry} -> {expiry_datetime.isoformat()}")
                elif isinstance(expiry, datetime):
                    expiry_datetime = expiry
                    logging.info(f"Microsoft token expiry from datetime: {expiry_datetime.isoformat()}")
            
            # Converti le date di scadenza Microsoft Graph
            microsoft_expiration_dt_inbound = None
            if microsoft_expiration_datetime_inbound:
                if isinstance(microsoft_expiration_datetime_inbound, str):
                    microsoft_expiration_dt_inbound = datetime.fromisoformat(microsoft_expiration_datetime_inbound.replace('Z', '+00:00'))
                elif isinstance(microsoft_expiration_datetime_inbound, datetime):
                    microsoft_expiration_dt_inbound = microsoft_expiration_datetime_inbound
            
            microsoft_expiration_dt_outbound = None
            if microsoft_expiration_datetime_outbound:
                if isinstance(microsoft_expiration_datetime_outbound, str):
                    microsoft_expiration_dt_outbound = datetime.fromisoformat(microsoft_expiration_datetime_outbound.replace('Z', '+00:00'))
                elif isinstance(microsoft_expiration_datetime_outbound, datetime):
                    microsoft_expiration_dt_outbound = microsoft_expiration_datetime_outbound

            # Verifica che il service_id esista con subscription_id corretto
            check_response = (
                self.supabase.table("subscription_services")
                .select("service_id")
                .eq("service_id", service_id)
                .eq("subscription_id", subscription_id)
                .execute()
            )
            
            if not check_response.data:
                logging.error(f"Service non trovato: service_id={service_id}, subscription_id={subscription_id}")
                raise ValueError(f"Service non trovato. Devi prima creare un service con create-new-service")
            
            # Se esiste, aggiorna
            data = {
                "email": email,
                "hashed_access_token": encrypted_access_token,
                "hashed_refresh_token": encrypted_refresh_token,
                "expiry_token": expiry_datetime.isoformat() if expiry_datetime else None,
                "calendar_provider": "microsoft"
            }
            
            # Aggiungi i campi Microsoft subscription se presenti
            if microsoft_subscription_id_inbound is not None:
                data["microsoft_subscription_id_inbound"] = microsoft_subscription_id_inbound
                data["email_provider"] = "microsoft"
            
            if microsoft_subscription_id_outbound is not None:
                data["microsoft_subscription_id_outbound"] = microsoft_subscription_id_outbound
                data["email_provider"] = "microsoft"
            
            if microsoft_expiration_dt_inbound is not None:
                data["microsoft_expiration_datetime_inbound"] = microsoft_expiration_dt_inbound.isoformat()
            
            if microsoft_expiration_dt_outbound is not None:
                data["microsoft_expiration_datetime_outbound"] = microsoft_expiration_dt_outbound.isoformat()
            
            response = self.supabase.table("subscription_services").update(data).eq("service_id", service_id).execute()
                
            if not response.data:
                logging.info(f"Errore nell'aggiornamento del service_id: {service_id}")
                return False
            return True
            
            return True

        except Exception as e:
            print(f"Errore nel salvataggio delle credenziali Microsoft: {e}")
            return False  

    def save_google_credentials(self, email: str, subscription_id: str, access_token: str, refresh_token: str, expiry, history_id: str = None, service_id: str = None) -> bool:
        """
        Salva le credenziali Google nel database per l'utente con l'email specificata.
        I token vengono cifrati prima del salvataggio.
        
        Args:
            email: Email dell'utente
            subscription_id: ID della subscription
            access_token: Token di accesso Google
            refresh_token: Token di refresh Google
            expiry: Data di scadenza del token
            history_id: ID dello storico Gmail (None se services="calendar")
            service_id: ID del service esistente da aggiornare (OBBLIGATORIO)
        """
        try:
            # service_id è obbligatorio
            if not service_id:
                logging.error("service_id mancante per save_google_credentials")
                raise ValueError("service_id è obbligatorio. Devi prima creare un service con create-new-service e passare il service_id")

            # Cifra i token prima del salvataggio
            encrypted_access_token = encrypt_token(access_token, "token")
            encrypted_refresh_token = encrypt_token(refresh_token, "token")
            
            # Verifica che il service_id esista con subscription_id corretto
            check_response = (
                self.supabase.table("subscription_services")
                .select("service_id")
                .eq("service_id", service_id)
                .eq("subscription_id", subscription_id)
                .execute()
            )
            
            if not check_response.data:
                logging.error(f"Service non trovato: service_id={service_id}, subscription_id={subscription_id}")
                raise ValueError(f"Service non trovato. Devi prima creare un service con create-new-service")
            
            # Se esiste, aggiorna
            data = {
                "email": email,
                "email_provider": "google" if history_id else None,
                "hashed_access_token": encrypted_access_token,
                "hashed_refresh_token": encrypted_refresh_token,
                "expiry_token": expiry.isoformat() if expiry else None,
                "calendar_provider": "google"
            }
            
            # Aggiungi history_id solo se non è None
            if history_id is not None:
                data["history_id"] = history_id
                data["email_provider"] = "google"
            
            # Rimuove le chiavi con valore None
            data = {k: v for k, v in data.items() if v is not None}
            
            response = self.supabase.table("subscription_services").update(data).eq("service_id", service_id).execute()
                
            if not response.data:
                logging.info(f"Errore nell'aggiornamento del service_id: {service_id}")
                return False
            return True
            
            return True

        except Exception as e:
            print(f"Errore nel salvataggio delle credenziali Google: {e}")
            return False

    def email_exists(self, email: str) -> bool:
        """
        Controlla se una mail esiste nel database subscription_services.
        """
        try:
            response = self.supabase.table("subscription_services").select("email").eq("email", email).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Errore nel controllo dell'esistenza della mail: {e}")
            return False

    def get_google_credentials(self, email: str) -> OAuthGoogleCredentials | None:
        """
        Recupera e decifra le credenziali Google per l'utente specificato.
        """
        try:
            response = self.supabase.table("subscription_services").select("*").eq("email", email).execute()
            if not response.data:
                return None
                
            credential = response.data[0]

            # Decifra i token
            decrypted_access_token = decrypt_token(credential["hashed_access_token"], cond="token")
            decrypted_refresh_token = decrypt_token(credential["hashed_refresh_token"], cond="token")
            
            # Converti expiry_token da string a datetime se necessario
            expiry_datetime = credential["expiry_token"]
            if isinstance(expiry_datetime, str):
                # Parse the datetime and convert to naive datetime (remove timezone info)
                # Google OAuth library expects naive datetimes
                if expiry_datetime.endswith('Z'):
                    expiry_datetime = expiry_datetime[:-1]  # Remove 'Z'
                elif '+' in expiry_datetime:
                    expiry_datetime = expiry_datetime.split('+')[0]  # Remove timezone offset
                expiry_datetime = datetime.fromisoformat(expiry_datetime)
            
            cred = OAuthGoogleCredentials(
                email=email,
                access_token=decrypted_access_token,
                refresh_token=decrypted_refresh_token,
                expiry=expiry_datetime,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                scopes=os.getenv("GOOGLE_SCOPES", "").split()
            )
            
            return cred
        except Exception as e:
            print(f"Errore nel recupero delle credenziali Google: {e}")
            return None

    def create_subscription_service(
        self,
        email: str = None,
        subscription_id: str = None,
        name: str = None,
        email_provider: str = None,
        calendar_provider: str = None,
        calendar_names: list = None,
        information: dict = None,
        imap_server: str = None,
        imap_port: int = None,
        smtp_server: str = None,
        smtp_port: int = None,
        hashed_password: str = None,
        hashed_access_token: str = None,
        hashed_refresh_token: str = None,
        expiry_token = None,
        confidence_response_threshold: float = None,
        confidence_review_mail: float = None,
        priority_threshold: float = None,
        confidence_classification_threshold: float = None,
        urgent_meeting_threshold: float = None,
        history_id: str = None,
        microsoft_subscription_id_inbound: str = None,
        microsoft_subscription_id_outbound: str = None,
        microsoft_expiration_datetime_inbound = None,
        microsoft_expiration_datetime_outbound = None,
        oauth_user_id: str = None,
        config_completed: bool = False,
        activated: bool = False,
        quiz_q_a: dict = None,
        last_sent_message_id: str = None,
        last_sent_timestamp: datetime = None,
        last_received_message_id: str = None,
        last_received_timestamp: datetime = None
    ) -> dict | None:
        try:
            data = {
                "email": email,
                "subscription_id": str(subscription_id) if subscription_id else None,
                "name": name,
                "email_provider": email_provider,
                "calendar_provider": calendar_provider,
                "calendar_names": calendar_names,
                "information": information,
                "imap_server": imap_server,
                "imap_port": imap_port,
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "hashed_password": hashed_password,
                "hashed_access_token": hashed_access_token,
                "hashed_refresh_token": hashed_refresh_token,
                "expiry_token": expiry_token.isoformat() if expiry_token else None,
                "confidence_response_threshold": "0.8",
                "confidence_review_mail": "0.7",
                "priority_threshold": "0.6",
                "confidence_classification_threshold": "0.75",
                "urgent_meeting_threshold": "0.9",
                "history_id": history_id,
                "microsoft_subscription_id_inbound": microsoft_subscription_id_inbound,
                "microsoft_subscription_id_outbound": microsoft_subscription_id_outbound,
                "microsoft_expiration_datetime_inbound": microsoft_expiration_datetime_inbound.isoformat() if microsoft_expiration_datetime_inbound else None,
                "microsoft_expiration_datetime_outbound": microsoft_expiration_datetime_outbound.isoformat() if microsoft_expiration_datetime_outbound else None,
                "oauth_user_id": oauth_user_id,
                "config_completed": config_completed,
                "activated": activated,
                "quiz_q_a": quiz_q_a,
                "last_sent_message_id": last_sent_message_id,
                "last_sent_timestamp": last_sent_timestamp.isoformat() if last_sent_timestamp else None,
                "last_received_message_id": last_received_message_id,
                "last_received_timestamp": last_received_timestamp.isoformat() if last_received_timestamp else None
            }

            
            # Rimuove le chiavi con valore None per permettere l'uso dei valori di default del database
            data = {k: v for k, v in data.items() if v is not None}
            
            # Inserisce il record nel database
            response = self.supabase.table("subscription_services").insert(data).execute()
                
            return response.data[0] if response.data else None
            
        except Exception as e:
            print(f"Errore nella creazione del subscription_service: {e}")
            return None

    def update_history_id(self, email: str, history_id: str) -> bool:
        """
        Aggiorna lo history_id per l'utente specificato.
        """

        # TODO sevo salvare qualche expiration date di google?

        try:
            data = {
                "history_id": history_id
            }
            response = self.supabase.table("subscription_services").update(data).eq("email", email).execute()
            
            if not response.data:
                print(f"Nessun record aggiornato per email: {email}")
                return False
            return True
        except Exception as e:
            print(f"Errore nell'aggiornamento dello history_id: {e}")
            return False

    def get_configuration(self, subscription_id: str):
        result = self.supabase.table("subscription_services").select(
            "subscription_id, confidence_response_threshold, confidence_review_mail, priority_threshold, confidence_classification_threshold, urgent_meeting_threshold, draft"
        ).eq("subscription_id", subscription_id).execute()

        if not result.data:
            return None
        
        return result.data[0]

    def update_configuration(self, subscription_id: str, updates: dict):
        config = SubscriptionServiceConfigCrate.model_validate(updates)

        upload_dict = config.model_dump()

        try:
            result = (
                self.supabase.table("subscription_services")
                .update(upload_dict)
                .eq("subscription_id", subscription_id)
                .execute()
            )
            return result.data[0]
        except Exception as e:
            print(f"Errore nell'aggiornamento della configurazione: {e}")
            return None

    def get_microsoft_credentials_inbound(self, microsoft_subscription_id_inbound: str) -> dict | None:
        """
        Recupera le credenziali Microsoft per subscription inbound dal database.
        """
        try:
            response = self.supabase.table("subscription_services").select("*").eq("microsoft_subscription_id_inbound", microsoft_subscription_id_inbound).execute()
            
            if not response.data:
                return None
            
            user_data = response.data[0]
            
            # Decrittare i token se presenti
            access_token = ""
            refresh_token = ""
            
            if user_data.get("hashed_access_token"):
                access_token = decrypt_token(user_data["hashed_access_token"], "token")
            
            if user_data.get("hashed_refresh_token"):
                refresh_token = decrypt_token(user_data["hashed_refresh_token"], "token")
            
            return {
                "email": user_data.get("email"),
                "oauth_user_id": user_data.get("oauth_user_id"),
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expiry": user_data.get("expiry_token"),
                "subscription_id": user_data.get("subscription_id"),
                "microsoft_subscription_id_inbound": user_data.get("microsoft_subscription_id_inbound"),
                "microsoft_expiration_datetime_inbound": user_data.get("microsoft_expiration_datetime_inbound")
            }
            
        except Exception as e:
            print(f"Errore nel recupero delle credenziali Microsoft inbound per subscription_id {microsoft_subscription_id_inbound}: {str(e)}")
            return None

    def get_microsoft_credentials_outbound(self, microsoft_subscription_id_outbound: str) -> dict | None:
        """
        Recupera le credenziali Microsoft per subscription outbound dal database.
        """
        try:
            response = self.supabase.table("subscription_services").select("*").eq("microsoft_subscription_id_outbound", microsoft_subscription_id_outbound).execute()
            
            if not response.data:
                return None
            
            user_data = response.data[0]
            
            # Decrittare i token se presenti
            access_token = ""
            refresh_token = ""
            
            if user_data.get("hashed_access_token"):
                access_token = decrypt_token(user_data["hashed_access_token"], "token")
            
            if user_data.get("hashed_refresh_token"):
                refresh_token = decrypt_token(user_data["hashed_refresh_token"], "token")
            
            return {
                "email": user_data.get("email"),
                "oauth_user_id": user_data.get("oauth_user_id"),
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expiry": user_data.get("expiry_token"),
                "subscription_id": user_data.get("subscription_id"),
                "microsoft_subscription_id_outbound": user_data.get("microsoft_subscription_id_outbound"),
                "microsoft_expiration_datetime_outbound": user_data.get("microsoft_expiration_datetime_outbound")
            }
            
        except Exception as e:
            print(f"Errore nel recupero delle credenziali Microsoft outbound per subscription_id {microsoft_subscription_id_outbound}: {str(e)}")
            return None

    def get_microsoft_credentials_by_email(self, email: str) -> dict | None:
        """
        Recupera le credenziali Microsoft complete (inbound + outbound) per email.
        """
        try:
            response = self.supabase.table("subscription_services").select("*").eq("email", email).execute()
            
            if not response.data:
                return None
            
            user_data = response.data[0]
            
            # Decrittare i token se presenti
            access_token = ""
            refresh_token = ""
            
            if user_data.get("hashed_access_token"):
                access_token = decrypt_token(user_data["hashed_access_token"], "token")
            
            if user_data.get("hashed_refresh_token"):
                refresh_token = decrypt_token(user_data["hashed_refresh_token"], "token")
            
            return {
                "email": user_data.get("email"),
                "oauth_user_id": user_data.get("oauth_user_id"),
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expiry": user_data.get("expiry_token"),
                "subscription_id": user_data.get("subscription_id"),
                "microsoft_subscription_id_inbound": user_data.get("microsoft_subscription_id_inbound"),
                "microsoft_subscription_id_outbound": user_data.get("microsoft_subscription_id_outbound"),
                "microsoft_expiration_datetime_inbound": user_data.get("microsoft_expiration_datetime_inbound"),
                "microsoft_expiration_datetime_outbound": user_data.get("microsoft_expiration_datetime_outbound")
            }
            
        except Exception as e:
            print(f"Errore nel recupero delle credenziali Microsoft per email {email}: {str(e)}")
            return None

    def get_services_by_subscription(self, subscription_id: str) -> List[SubscriptionServiceRead]:
        resp = (
            self.supabase
            .table("subscription_services")
            .select("*")
            .eq("subscription_id", subscription_id)
            .execute()
        )

        if not resp.data:
            return []

        return [SubscriptionServiceRead(**service) for service in resp.data]

    def update_qdrant_collection(self, service_id: str, collection_name: str) -> bool:
        """
        Update the qdrant_collection field for a subscription service.
        
        Args:
            service_id: The service_id (UUID) of the subscription service
            collection_name: The name of the Qdrant collection
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                "qdrant_collection": collection_name
            }
            response = (
                self.supabase.table("subscription_services")
                .update(data)
                .eq("service_id", service_id)
                .execute()
            )
            
            if not response.data:
                print(f"No record updated for service_id: {service_id}")
                return False
            return True
        except Exception as e:
            print(f"Error updating qdrant_collection: {e}")
            return False

    def update_qdrant_collection_by_email(self, email: str, collection_name: str) -> bool:
        """Update qdrant_collection for a subscription service identified by email."""
        try:
            data = {"qdrant_collection": collection_name}
            response = (
                self.supabase.table("subscription_services")
                .update(data)
                .eq("email", email)
                .execute()
            )
            if not response.data:
                print(f"No record updated for email: {email}")
                return False
            return True
        except Exception as e:
            print(f"Error updating qdrant_collection by email: {e}")
            return False

    def update_scraping_collection_path_by_email(self, email: str, scraping_collection_path: str | None) -> bool:
        """Update scraping_collection_path for a subscription service identified by email."""
        try:
            data = {"scraping_collection_path": scraping_collection_path}
            response = (
                self.supabase.table("subscription_services")
                .update(data)
                .eq("email", email)
                .execute()
            )
            if not response.data:
                print(f"No record updated for email: {email}")
                return False
            return True
        except Exception as e:
            print(f"Error updating scraping_collection_path by email: {e}")
            return False

    def get_qdrant_collection(self, service_id: str) -> str | None:
        """
        Get the qdrant_collection name for a subscription service.
        
        Args:
            service_id: The service_id (UUID) of the subscription service
            
        Returns:
            The collection name or None if not found
        """
        try:
            response = (
                self.supabase.table("subscription_services")
                .select("qdrant_collection")
                .eq("service_id", service_id)
                .execute()
            )
            
            if not response.data:
                return None
            
            return response.data[0].get("qdrant_collection")
        except Exception as e:
            print(f"Error getting qdrant_collection: {e}")
            return None

    def get_qdrant_collection_by_email(self, email: str) -> str | None:
        """Get qdrant_collection for a subscription service identified by email."""
        try:
            response = (
                self.supabase.table("subscription_services")
                .select("qdrant_collection")
                .eq("email", email)
                .execute()
            )
            if not response.data:
                return None
            return response.data[0].get("qdrant_collection")
        except Exception as e:
            print(f"Error getting qdrant_collection by email: {e}")
            return None

    def get_service_by_email(self, email: str) -> dict | None:
        """Get subscription service by unique email."""
        try:
            response = (
                self.supabase.table("subscription_services")
                .select("*")
                .eq("email", email)
                .execute()
            )
            if not response.data:
                return None
            return response.data[0]
        except Exception as e:
            print(f"Error getting service by email: {e}")
            return None
    
    def get_calendar_information(self, email: str) -> dict | None:
        try:
            resp = (
                self.supabase
                .table("subscription_services")
                .select("business_hours, appointment_duration")
                .eq("email", email)
                .execute()
            )
            
            if not resp.data:
                return None
            
            return {
                "business_hours": resp.data[0].get("business_hours"),
                "appointment_duration": resp.data[0].get("appointment_duration")
            }
        except Exception as e:
            print(f"Errore nel recupero delle informazioni del calendario: {e}")
            return None

    def update_subscription_website_by_email(self, email: str, website_url: str) -> bool:
        """
        Update the website field in the subscriptions table for a user identified by email.
        
        This method first retrieves the subscription_id from subscription_services table
        using the email, then updates the subscriptions table.
        
        Args:
            email: The email address to look up
            website_url: The website URL to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Step 1: Get subscription_id from subscription_services using email
            response = (
                self.supabase.table("subscription_services")
                .select("subscription_id")
                .eq("email", email)
                .execute()
            )
            
            if not response.data or not response.data[0].get("subscription_id"):
                print(f"[DAO] No subscription_id found for email: {email}")
                return False
            
            subscription_id = response.data[0]["subscription_id"]
            
            # Step 2: Update subscriptions table with the website
            update_response = (
                self.supabase.table("subscriptions")
                .update({"website": website_url})
                .eq("subscription_id", subscription_id)
                .execute()
            )
            
            if not update_response.data:
                print(f"[DAO] Failed to update website for subscription_id: {subscription_id}")
                return False
            
            print(f"[DAO] Updated website to '{website_url}' for email: {email}")
            return True
            
        except Exception as e:
            print(f"[DAO] Error updating subscription website: {e}")
            return False
    
    def get_information(self, email: str) -> str | None:
        try:
            resp = (
                self.supabase
                .table("subscription_services")
                .select("information")
                .eq("email", email)
                .execute()
            )

            if not resp.data:
                return None
            
            return resp.data[0].get("information")
        except Exception as e:
            print(f"Errore nel recupero di information: {e}")
            return None
    
    def update_information(self, email: str, information: str) -> str | None:
        try:
            resp = (
                self.supabase
                .table("subscription_services")
                .update({"information": information})
                .eq("email", email)
                .execute()
            )
            
            if not resp.data:
                return None
            
            return resp.data[0].get("information")
        except Exception as e:
            print(f"Errore nell'aggiornamento di information: {e}")
            return None
    
    def get_service_settings(self, email: str) -> dict | None:
        try:
            result = (
                self.supabase
                .table("subscription_services")
                .select("business_hours, appointment_duration, email_signature, tone_of_voice, phone_numbers")
                .eq("email", email)
                .execute()
            )
            
            if not result.data:
                return None
            
            return result.data[0]
        except Exception as e:
            print(f"Errore nel recupero settings servizio: {e}")
            return None
    
    def update_service_settings(self, email: str, updates: dict) -> dict | None:
        try:
            allowed_fields = {"business_hours", "appointment_duration", "email_signature", "tone_of_voice", "phone_numbers"}
            filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
            
            if not filtered_updates:
                raise ValueError("Nessun campo valido da aggiornare")
            
            result = (
                self.supabase
                .table("subscription_services")
                .update(filtered_updates)
                .eq("email", email)
                .execute()
            )
            
            if not result.data:
                return None
            
            return result.data[0]
        except Exception as e:
            print(f"Errore nell'aggiornamento settings servizio: {e}")
            return None
    
    def static_quiz(self, email: str, payload: dict) -> bool:
        try:
            update_data = {k: v for k, v in payload.items() if v is not None}
            
            if not update_data:
                return None
            
            resp = (
                self.supabase
                .table("subscription_services")
                .update(update_data)
                .eq("email", email)
                .execute()
            )
            
            if not resp.data:
                return False
            
            return True
        except Exception as e:
            print(f"Errore nell'aggiornamento dei dati static quiz: {e}")
            return None