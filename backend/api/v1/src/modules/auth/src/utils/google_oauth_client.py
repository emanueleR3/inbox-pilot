from google_auth_oauthlib.flow import Flow
from src.core.config import settings
from dotenv import load_dotenv
import os

load_dotenv()

# Imposta sempre per risolvere il problema del reverse proxy
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def create_google_flow(services="all"):
    """
    Crea un flusso OAuth2 per Google con scope specifici.
    
    Args:
        services (str): "all" per tutti i permessi, "calendar" per solo calendar
    """
    # Definisci scope basati sui servizi richiesti
    if services == "calendar":
        scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events", 
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid"
        ]
    else:  # services == "all" o qualsiasi altro valore
        # Parse degli scope dalla variabile d'ambiente se presente
        scopes_env = os.getenv("GOOGLE_SCOPES", "")
        if scopes_env:
            scopes = [scope.strip() for scope in scopes_env.split() if scope.strip()]
        else:
            # Fallback agli scope completi
            scopes = [
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.readonly", 
                "https://www.googleapis.com/auth/gmail.send",
                #"https://www.googleapis.com/auth/gmail.metadata",
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/calendar.events", 
                "https://www.googleapis.com/auth/calendar.readonly",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
                "openid"
            ]
    
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
    
    # Disabilita il controllo HTTPS quando si è dietro un reverse proxy (produzione)
    # Questo è necessario perché nginx termina SSL e inoltra richieste HTTP a FastAPI
    env = os.getenv("ENV", "development")
    
    # Per ora impostiamo sempre per risolvere il problema del reverse proxy
    # TODO: rimuovere in development quando non necessario
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    # Log per debug
    from src.core.logger import setup_logger
    logger = setup_logger()
    logger.info(f"Environment: {env}")
    logger.info(f"OAUTHLIB_INSECURE_TRANSPORT set to: {os.environ.get('OAUTHLIB_INSECURE_TRANSPORT')}")
    
    return flow

    '''
        scopes=[
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            #"https://www.googleapis.com/auth/gmail.metadata",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid"
        ],
    '''