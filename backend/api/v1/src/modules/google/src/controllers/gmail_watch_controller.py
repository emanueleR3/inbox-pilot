from googleapiclient.discovery import build
from src.core.config import settings
from src.modules.auth.src.utils.google_oauth_client import get_credentials_for_user

def create_watch_for_user(user_email: str):
    """
    Attiva watch Gmail per un utente
    """
    credentials = get_credentials_for_user(user_email)
    service = build("gmail", "v1", credentials=credentials)

    # TODO controllare 
    request = {
        "labelIds": ["INBOX"],
        "topicName": settings.PUBSUB_TOPIC_PATH
    }

    response = service.users().watch(userId="me", body=request).execute()
    return response  # contiene historyId e expiration