from google_auth_oauthlib.flow import Flow
from src.core.config import settings
from dotenv import load_dotenv
import os

load_dotenv()

def create_google_flow():
    """
    Crea un flusso OAuth2 per Google.
    """
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
            "https://www.googleapis.com/auth/gmail.metadata",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events", 
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid"
        ]
    
    print(f"🔧 Scope richiesti: {scopes}")
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=scopes,
    )

    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow

    '''
        scopes=[
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.metadata",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid"
        ],
    '''