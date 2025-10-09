from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.utils.db_client import get_user_credentials  # funzione che legge token dal DB

def get_service_for_user(email: str):
    """
    Restituisce un oggetto Gmail API per un utente
    """
    creds_data = get_user_credentials(email)
    creds = Credentials(
        token=creds_data['access_token'],
        refresh_token=creds_data['refresh_token'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data['client_id'],
        client_secret=creds_data['client_secret'],
        scopes=creds_data['scopes']
    )

    service = build('gmail', 'v1', credentials=creds)
    return service