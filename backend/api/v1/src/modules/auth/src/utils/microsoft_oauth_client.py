import httpx
import secrets
import os
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("MICROSOFT_APPLICATION_ID_CLIENT")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET_VALUE")
REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI")
AUTHORITY = os.getenv("MICROSOFT_AUTHORITY")
AUTH_URL = os.getenv("MICROSOFT_AUTH_URL")
TOKEN_URL = os.getenv("MICROSOFT_TOKEN_URL")
SCOPES_STRING = os.getenv("MICROSOFT_SCOPES", "")
# Converti la stringa degli scope in una lista
if SCOPES_STRING:
    SCOPES = SCOPES_STRING.split(" ")
else:
    # Scope di default per Microsoft Graph
    SCOPES = [
        #"https://graph.microsoft.com/Mail.Read",
        #"https://graph.microsoft.com/Mail.Send", 
        #"https://graph.microsoft.com/User.Read",
        "openid",
        "profile", 
        "email", 
        "offline_access",
        "User.Read",
        "Mail.Send",
        "Mail.ReadWrite",
        "Calendars.ReadWrite"
    ]

def get_scopes_for_services(services="all"):
    """
    Restituisce gli scope Microsoft in base ai servizi richiesti.
    
    Args:
        services (str): "all" per tutti i permessi, "calendar" per solo calendar
    """
    if services == "calendar":
        return [
            "openid",
            "profile", 
            "email", 
            "offline_access",
            "User.Read",
            "Calendars.ReadWrite"
        ]
    else:  # services == "all" o qualsiasi altro valore
        # Parse dalla variabile d'ambiente se presente
        scopes_env = os.getenv("MICROSOFT_SCOPES", "")
        if scopes_env:
            return scopes_env.split(" ")
        else:
            # Scope completi di default
            return [
                "openid",
                "profile", 
                "email", 
                "offline_access",
                "User.Read",
                "Mail.Send",
                "Mail.ReadWrite",
                "Calendars.ReadWrite"
            ]

def get_auth_url(state: str, services="all"):
    """
    Genera l'URL di autenticazione Microsoft con scope specifici.
    """
    scopes = get_scopes_for_services(services)
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": " ".join(scopes),
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"

async def exchange_code_for_tokens(code: str, services="all"):
    """
    Scambia il codice di autorizzazione con i token, usando gli scope specifici.
    """
    scopes = get_scopes_for_services(services)
    async with httpx.AsyncClient() as client:
        data = {
            "client_id": CLIENT_ID,
            "scope": " ".join(scopes),
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
            "client_secret": CLIENT_SECRET,
        }
        response = await client.post(TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()

async def refresh_access_token(refresh_token: str, services="all"):
    """
    Rinnova i token usando il refresh token con scope specifici.
    """
    scopes = get_scopes_for_services(services)
    async with httpx.AsyncClient() as client:
        data = {
            "client_id": CLIENT_ID,
            "scope": " ".join(scopes),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_secret": CLIENT_SECRET,
        }
        response = await client.post(TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()
    
def create_microsoft_auth_url(custom_state: str = None, services="all"):
    """
    Restituisce l'URL di login Microsoft pronto per il redirect.
    Se custom_state è fornito, lo usa; altrimenti genera uno state casuale.
    
    Args:
        custom_state (str): Stato personalizzato (contiene subscription_id e services)
        services (str): "all" per tutti i permessi, "calendar" per solo calendar
    """
    from src.core.logger import setup_logger
    logger = setup_logger()
    
    # Se abbiamo uno state personalizzato, estraiamo i servizi da lì
    if custom_state:
        state = custom_state
        logger.info(f"Using custom state for Microsoft OAuth: {state[:20]}...")
        
        # Prova a decodificare lo state per estrarre services
        try:
            import json
            import base64
            decoded_state = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
            services = decoded_state.get("services", "all")
            logger.info(f"Extracted services from state: {services}")
        except Exception as e:
            logger.warning(f"Could not decode state for services: {e}")
            services = "all"  # fallback
    else:
        state = secrets.token_urlsafe(16)  # genera uno state sicuro di default
        logger.info(f"Generated random state for Microsoft OAuth: {state}")
    
    auth_url = get_auth_url(state, services)
    
    # Log per debug
    scopes = get_scopes_for_services(services)
    logger.info(f"Microsoft scopes for '{services}': {scopes}")
    logger.info(f"Microsoft auth URL: {auth_url}")
    
    return auth_url