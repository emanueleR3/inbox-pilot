from src.core.database import get_supabase_client
from cryptography.fernet import Fernet
import base64
import hashlib
import os
import logging
from dotenv import load_dotenv
from src.core.model.subscription_service import OAuthGoogleCredentials, SubscriptionServiceCrate, SubscriptionServiceConfigCrate, SubscriptionServiceRead
from datetime import datetime, timedelta, timezone

load_dotenv()

class SubscriptionServiceDAO:
    def __init__(self):
        self.supabase = get_supabase_client()

        encryption_key_token = os.getenv("ENCRYPTION_KEY_TOKEN")
        encryption_key_pass = os.getenv("ENCRYPTION_KEY_PASS")

        if not encryption_key_token:
            raise ValueError("ENCRYPTION_KEY_TOKEN non trovata nelle variabili d'ambiente")
        if not encryption_key_pass:
            raise ValueError("ENCRYPTION_KEY_PASS non trovata nelle variabili d'ambiente")
        
        self._encryption_key_token = encryption_key_token.encode()
        key_hash_token = hashlib.sha256(self._encryption_key_token).digest()
        self._fernet_key_token = base64.urlsafe_b64encode(key_hash_token)
        self._cipher_token = Fernet(self._fernet_key_token)

        self._encryption_key_pass = encryption_key_pass.encode()
        key_hash_pass = hashlib.sha256(self._encryption_key_pass).digest()
        self._fernet_key_pass = base64.urlsafe_b64encode(key_hash_pass)
        self._cipher_pass = Fernet(self._fernet_key_pass)

    def _encrypt(self, token: str, cond: str) -> str:
        """
        Cifra un token usando Fernet (AES-256).
        """
        if not token:
            return ""

        if cond not in ("token", "pass"):
            raise ValueError("cond deve essere 'token' o 'pass'")

        cipher_attr = f"_cipher_{cond}"
        cipher = getattr(self, cipher_attr, None)

        if cipher is None:
            raise ValueError(f"Cifrario {cipher_attr} non trovato nella classe")

        return cipher.encrypt(token.encode()).decode()

    def _decrypt(self, encrypted_token: str, cond: str) -> str:
        if not encrypted_token:
            return ""
        if not encrypted_token:
            return ""

        if cond not in ("token", "pass"):
            raise ValueError("cond deve essere 'token' o 'pass'")

        cipher_attr = f"_cipher_{cond}"
        cipher = getattr(self, cipher_attr, None)

        if cipher is None:
            raise ValueError(f"Cifrario {cipher_attr} non trovato nella classe")

        return cipher.decrypt(encrypted_token.encode()).decode()
    
    def save_custom_provider_credentials(self, server_imap: str, server_smtp: str, imap_port: int, smtp_port: int, email: str, password: str, subscription_id: str) -> bool:
        try:
            encrypted_password = self._encrypt(password, "pass")
            
            email_exists = self.email_exists(email)
            if email_exists:
                # rimuovi i token di accesso precedenti se esistono
                data = {
                    "email_provider": "imap",
                    "imap_server": server_imap, 
                    "smtp_server": server_smtp, 
                    "imap_port": imap_port, 
                    "smtp_port": smtp_port, 
                    "hashed_password": encrypted_password, 
                    "hashed_access_token": None,
                    "hashed_refresh_token": None,
                    "expiry_token": None
                }
                response = self.supabase.table("subscription_services").update(data).eq("email", email).execute()
                if not response.data:
                    logging.info(f"Nessun record aggiornato per email: {email}")
                    return False
                return True
            else:
                response = self.create_subscription_service(
                    email=email,
                    email_provider="imap",
                    imap_server=server_imap, 
                    smtp_server=server_smtp, 
                    imap_port=imap_port, 
                    smtp_port=smtp_port, 
                    hashed_password=encrypted_password, 
                    subscription_id=subscription_id
                )

                if response is None:
                    logging.info(f"Errore nella creazione del nuovo record per email: {email}")
                    return False
                
                return True
        except Exception as e:
            raise e


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
        microsoft_expiration_datetime_outbound = None
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
        """
        try:
            # Cifra i token prima del salvataggio
            encrypted_access_token = self._encrypt(access_token, "token")
            encrypted_refresh_token = self._encrypt(refresh_token, "token")

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

            # Controllo se esiste già un record con questa email
            email_exists = self.email_exists(email)
            if email_exists:
                # Aggiorna il record esistente
                data = {
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
                
                response = self.supabase.table("subscription_services").update(data).eq("email", email).execute()
                    
                if not response.data:
                    logging.info(f"Nessun record aggiornato per email: {email}")
                    return False
            else:
                # Crea un nuovo record
                response = self.create_subscription_service(
                    email=email,
                    email_provider="microsoft",
                    subscription_id=str(subscription_id),
                    hashed_access_token=encrypted_access_token,
                    hashed_refresh_token=encrypted_refresh_token,
                    expiry_token=expiry_datetime,
                    microsoft_subscription_id_inbound=microsoft_subscription_id_inbound,
                    microsoft_subscription_id_outbound=microsoft_subscription_id_outbound,
                    microsoft_expiration_datetime_inbound=microsoft_expiration_dt_inbound,
                    microsoft_expiration_datetime_outbound=microsoft_expiration_dt_outbound,
                    calendar_provider="microsoft",
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

    def save_google_credentials(self, email: str, subscription_id: str, access_token: str, refresh_token: str, expiry, history_id: str = None) -> bool:
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
            calendar_provider: Provider del calendar ("google" se services="calendar", None se services="all")
        """
        try:
            # Cifra i token prima del salvataggio
            encrypted_access_token = self._encrypt(access_token, "token")
            encrypted_refresh_token = self._encrypt(refresh_token, "token")
            
            # controllo se esiste già un record con questa email
            email_exists = self.email_exists(email)
            if email_exists:
                # Aggiorna il record esistente
                data = {
                    "hashed_access_token": encrypted_access_token,
                    "hashed_refresh_token": encrypted_refresh_token,
                    "expiry_token": expiry.isoformat() if expiry else None,
                    "calendar_provider": "google"
                }
                
                # Aggiungi history_id solo se non è None
                if history_id is not None:
                    data["history_id"] = history_id
                    data["email_provider"] = "google"
                
                response = self.supabase.table("subscription_services").update(data).eq("email", email).execute()
                    
                if not response.data:
                    logging.info(f"Nessun record aggiornato per email: {email}")
                    return False
            else:
                # Crea un nuovo record
                response = self.create_subscription_service(
                    email=email,
                    email_provider="google",
                    subscription_id=subscription_id,
                    hashed_access_token=encrypted_access_token,
                    hashed_refresh_token=encrypted_refresh_token,
                    expiry_token=expiry,
                    config_completed=False,
                    activated=False,
                    history_id=history_id,  # Può essere None
                    calendar_provider="google"
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
            decrypted_access_token = self._decrypt(credential["hashed_access_token"], cond="token")
            decrypted_refresh_token = self._decrypt(credential["hashed_refresh_token"], cond="token")
            
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
            data = {
                "email": email,
                "subscription_id": str(subscription_id) if subscription_id else None,
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

    def get_configuration(self, subscription_id: str):
        result = self.supabase.table("subscription_services").select(
            "subscription_id, confidence_response_threshold, confidence_review_mail, priority_threshold, confidence_classification_threshold, urgent_meeting_threshold"
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
                access_token = self._decrypt(user_data["hashed_access_token"], "token")
            
            if user_data.get("hashed_refresh_token"):
                refresh_token = self._decrypt(user_data["hashed_refresh_token"], "token")
            
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
                access_token = self._decrypt(user_data["hashed_access_token"], "token")
            
            if user_data.get("hashed_refresh_token"):
                refresh_token = self._decrypt(user_data["hashed_refresh_token"], "token")
            
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
                access_token = self._decrypt(user_data["hashed_access_token"], "token")
            
            if user_data.get("hashed_refresh_token"):
                refresh_token = self._decrypt(user_data["hashed_refresh_token"], "token")
            
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
