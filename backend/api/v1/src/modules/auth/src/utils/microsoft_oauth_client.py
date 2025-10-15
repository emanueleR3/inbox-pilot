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
SCOPES = os.getenv("MICROSOFT_SCOPES")
#SCOPES = os.getenv("MICROSOFT_SCOPES").split(" ")

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
    
def create_microsoft_auth_url():
    """
    Restituisce l'URL di login Microsoft pronto per il redirect.
    Genera uno state casuale per protezione CSRF.
    """
    state = secrets.token_urlsafe(16)  # genera uno state sicuro
    return get_auth_url(state)