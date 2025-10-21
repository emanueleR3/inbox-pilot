from fastapi import HTTPException
from src.core.database import get_supabase_client
from cryptography.fernet import Fernet
import base64
import hashlib
import os
import logging
from dotenv import load_dotenv
from src.core.model.subscription_service import OAuthGoogleCredentials, SubscriptionServiceCrate, SubscriptionServiceConfigCrate, SubscriptionServiceRead
from datetime import datetime
from supabase import Client # TODO controllare se eliminare
from supabase_auth.errors import AuthApiError
from pydantic import ValidationError
from uuid import UUID

load_dotenv()

class SubscriptionServiceDAO:
    def __init__(self):
        self.supabase = get_supabase_client()
        # Chiave di cifratura da variabile d'ambiente
        encryption_key_str = os.getenv("ENCRYPTION_KEY")
        if not encryption_key_str:
            raise ValueError("ENCRYPTION_KEY non trovata nelle variabili d'ambiente")
        self._encryption_key = encryption_key_str.encode()
        # Genera la chiave Fernet da quella base
        key_hash = hashlib.sha256(self._encryption_key).digest()
        self._fernet_key = base64.urlsafe_b64encode(key_hash)
        self._cipher = Fernet(self._fernet_key)

    def _encrypt_token(self, token: str) -> str:
        """
        Cifra un token usando Fernet (AES-256).
        """
        if not token:
            return ""
        return self._cipher.encrypt(token.encode()).decode()

    def _decrypt_token(self, encrypted_token: str) -> str:
        """
        Decifra un token cifrato.
        """
        if not encrypted_token:
            return ""
        return self._cipher.decrypt(encrypted_token.encode()).decode()
    
    '''
                result = SubscriptionServiceDAO.save_microsoft_credentials(
            email, 
            subscription_id,
            access_token,
            refresh_token,
            expiry,
            subscription.get("id"),
            subscription.get("expirationDateTime")
        )
    '''  

    def save_microsoft_credentials(
        self, 
        email: str, 
        subscription_id: str, 
        access_token: str, 
        refresh_token: str, 
        expiry,
        microsoft_subscription_id: str,
        microsoft_expiration_datetime
    ) -> bool:
        """
        Salva le credenziali Microsoft nel database per l'utente con l'email specificata.
        I token vengono cifrati prima del salvataggio.
        """
        try:
            # Cifra i token prima del salvataggio
            encrypted_access_token = self._encrypt_token(access_token)
            encrypted_refresh_token = self._encrypt_token(refresh_token)

            # Converti expiry (Unix timestamp) e microsoft_expiration_datetime (ISO string) in oggetti datetime
            expiry_datetime = None
            if expiry:
                # Se expiry è un numero (Unix timestamp), convertilo in datetime
                if isinstance(expiry, (int, float)):
                    expiry_datetime = datetime.fromtimestamp(expiry)
                # Se expiry è già una stringa ISO, parsala
                elif isinstance(expiry, str):
                    expiry_datetime = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                # Se è già un datetime, usalo direttamente
                elif isinstance(expiry, datetime):
                    expiry_datetime = expiry
            
            microsoft_expiration_dt = None
            if microsoft_expiration_datetime:
                # Microsoft restituisce solitamente date in formato ISO string
                if isinstance(microsoft_expiration_datetime, str):
                    # Rimuovi 'Z' e sostituisci con '+00:00' per il parsing corretto
                    microsoft_expiration_dt = datetime.fromisoformat(microsoft_expiration_datetime.replace('Z', '+00:00'))
                elif isinstance(microsoft_expiration_datetime, datetime):
                    microsoft_expiration_dt = microsoft_expiration_datetime

            
            # controllo se esiste già un record con questa email
            email_exists = self.email_exists(email)
            if email_exists:
                # Aggiorna il record esistente
                data = {
                    "hashed_access_token": encrypted_access_token,
                    "hashed_refresh_token": encrypted_refresh_token,
                    "expiry_token": expiry_datetime.isoformat() if expiry_datetime else None,
                    "microsoft_subscription_id": microsoft_subscription_id,
                    "microsoft_expiration_datetime": microsoft_expiration_dt.isoformat() if microsoft_expiration_dt else None
                }
                response = self.supabase.table("subscription_services").update(data).eq("email", email).execute()
                    
                if not response.data:
                    logging.info(f"Nessun record aggiornato per email: {email}")
                    return False
            else:
                # Crea un nuovo record
                response = self.create_subscription_service(
                    email=email,
                    subscription_id=str(subscription_id),
                    hashed_access_token=encrypted_access_token,
                    hashed_refresh_token=encrypted_refresh_token,
                    expiry_token=expiry_datetime,
                    microsoft_subscription_id=microsoft_subscription_id,
                    microsoft_expiration_datetime=microsoft_expiration_dt,
                    config_completed=False,
                    activated=False
                )
                
                if response is None:
                    logging.info(f"Errore nella creazione del nuovo record per email: {email}")
                    return False
            
            return True

        except Exception as e:
            print(f"Errore nel salvataggio delle credenziali Microsoft: {e}")
            return False  

    def save_google_credentials(self, email: str, subscription_id: str, access_token: str, refresh_token: str, expiry) -> bool:
        """
        Salva le credenziali Google nel database per l'utente con l'email specificata.
        I token vengono cifrati prima del salvataggio.
        """
        try:
            # Cifra i token prima del salvataggio
            encrypted_access_token = self._encrypt_token(access_token)
            encrypted_refresh_token = self._encrypt_token(refresh_token)
            
            # controllo se esiste già un record con questa email
            email_exists = self.email_exists(email)
            if email_exists:
                # Aggiorna il record esistente
                data = {
                    "hashed_access_token": encrypted_access_token,
                    "hashed_refresh_token": encrypted_refresh_token,
                    "expiry_token": expiry.isoformat() if expiry else None
                }
                response = self.supabase.table("subscription_services").update(data).eq("email", email).execute()
                    
                if not response.data:
                    logging.info(f"Nessun record aggiornato per email: {email}")
                    return False
            else:
                # Crea un nuovo record
                response = self.create_subscription_service(
                    email=email,
                    subscription_id=subscription_id,
                    hashed_access_token=encrypted_access_token,
                    hashed_refresh_token=encrypted_refresh_token,
                    expiry_token=expiry,
                    config_completed=False,
                    activated=False
                )
                
                if response is None:
                    logging.info(f"Errore nella creazione del nuovo record per email: {email}")
                    return False
            
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
            decrypted_access_token = self._decrypt_token(credential["hashed_access_token"])
            decrypted_refresh_token = self._decrypt_token(credential["hashed_refresh_token"])
            
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
        email: str,
        subscription_id: str = None,
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
        microsoft_subscription_id: str = None,
        microsoft_expiration_datetime = None,
        oauth_user_id: str = None,
        config_completed: bool = False,
        activated: bool = False
    ) -> dict | None:
        """
        Crea un nuovo record nella tabella subscription_services.
        Tutti i parametri sono opzionali tranne email.
        I valori None vengono inseriti come NULL nel database.
        
        Returns:
            dict: Il record creato se successo, None se errore
        """
        try:
            # Prepara i dati per l'inserimento
            data = {
                "email": email,
                "subscription_id": str(subscription_id) if subscription_id else None,
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
                "confidence_response_threshold": confidence_response_threshold,
                "confidence_review_mail": confidence_review_mail,
                "priority_threshold": priority_threshold,
                "confidence_classification_threshold": confidence_classification_threshold,
                "urgent_meeting_threshold": urgent_meeting_threshold,
                "history_id": history_id,
                "microsoft_subscription_id": microsoft_subscription_id,
                "microsoft_expiration_datetime": microsoft_expiration_datetime.isoformat() if microsoft_expiration_datetime else None,
                "oauth_user_id": oauth_user_id,
                "config_completed": config_completed,
                "activated": activated
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
