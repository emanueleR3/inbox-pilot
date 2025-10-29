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

def get_auth_url(state: str):
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"

async def exchange_code_for_tokens(code: str):
    async with httpx.AsyncClient() as client:
        data = {
            "client_id": CLIENT_ID,
            "scope": " ".join(SCOPES),
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
            "client_secret": CLIENT_SECRET,
        }
        response = await client.post(TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()

async def refresh_access_token(refresh_token: str):
    async with httpx.AsyncClient() as client:
        data = {
            "client_id": CLIENT_ID,
            "scope": " ".join(SCOPES),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_secret": CLIENT_SECRET,
        }
        response = await client.post(TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()
    
def create_microsoft_auth_url(custom_state: str = None):
    """
    Restituisce l'URL di login Microsoft pronto per il redirect.
    Se custom_state è fornito, lo usa; altrimenti genera uno state casuale.
    """
    from src.core.logger import setup_logger
    logger = setup_logger()
    
    if custom_state:
        state = custom_state
        logger.info(f"Using custom state for Microsoft OAuth: {state[:20]}...")
    else:
        state = secrets.token_urlsafe(16)  # genera uno state sicuro di default
        logger.info(f"Generated random state for Microsoft OAuth: {state}")
    
    auth_url = get_auth_url(state)
    
    # Log per debug
    logger.info(f"Microsoft scopes: {SCOPES}")
    logger.info(f"Microsoft auth URL: {auth_url}")
    
    return auth_url