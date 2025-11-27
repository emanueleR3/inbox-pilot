from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.db_client import get_user_credentials  # funzione che legge token dal DB
from dotenv import load_dotenv
import os

load_dotenv()

def get_service_for_user(email: str):
    """
    Restituisce un oggetto Gmail API per un utente
    """
    creds_data = get_user_credentials(email)
    
    # Parse degli scope dalla variabile d'ambiente
    scopes_env = os.getenv("GOOGLE_SCOPES", "")
    if scopes_env:
        scopes = [scope.strip() for scope in scopes_env.split() if scope.strip()]
    else:
        # Fallback agli scope hardcoded
        scopes = [
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.readonly", 
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events", 
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid"
        ]
    

    print("\n\nDEBUG --- Access Token:", access_token)
    creds = Credentials(
        token=creds_data['access_token'],
        refresh_token=creds_data['refresh_token'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=scopes
    )

    service = build('gmail', 'v1', credentials=creds)
    return service