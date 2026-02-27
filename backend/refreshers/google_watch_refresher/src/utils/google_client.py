import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

GOOGLE_PUBSUB_TOPIC_PATH = os.getenv("GOOGLE_PUBSUB_TOPIC_PATH")


def renew_gmail_watch(access_token: str, refresh_token: str) -> dict:
    """
    Rinnova la watch Gmail per un utente chiamando users().watch().

    La chiamata è idempotente: se una watch è già attiva per lo stesso topic,
    Gmail la sostituisce con una nuova (aggiornando l'expiration).

    Docs: https://developers.google.com/gmail/api/reference/rest/v1/users/watch

    Args:
        access_token: Token di accesso OAuth2 dell'utente.
        refresh_token: Token di refresh OAuth2 dell'utente.

    Returns:
        dict con 'historyId' e 'expiration' (timestamp ms) della nuova watch.

    Raises:
        Exception se la chiamata API fallisce.
    """
    if not GOOGLE_PUBSUB_TOPIC_PATH:
        raise ValueError(
            "GOOGLE_PUBSUB_TOPIC_PATH non configurato nelle variabili d'ambiente"
        )

    # Parse degli scope dalla variabile d'ambiente
    scopes_env = os.getenv("GOOGLE_SCOPES", "")
    if scopes_env:
        scopes = [scope.strip() for scope in scopes_env.split() if scope.strip()]
    else:
        scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid",
        ]

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=scopes,
    )

    service = build("gmail", "v1", credentials=creds)

    request_body = {
        "labelIds": ["INBOX"],
        "topicName": GOOGLE_PUBSUB_TOPIC_PATH,
    }

    response = service.users().watch(userId="me", body=request_body).execute()
    return response
