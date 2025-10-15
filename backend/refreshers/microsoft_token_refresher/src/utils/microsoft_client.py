import httpx
import os
from dotenv import load_dotenv

load_dotenv()

MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
CLIENT_ID = os.getenv("MICROSOFT_APPLICATION_ID_CLIENT")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET_VALUE")
SCOPES = os.getenv("MICROSOFT_SCOPES").split(" ")

async def refresh_microsoft_token(refresh_token: str):
    """
    Usa il refresh_token per ottenere un nuovo access_token da Microsoft.
    """
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": " ".join(SCOPES),
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(MICROSOFT_TOKEN_URL, data=data)
        if resp.status_code != 200:
            raise Exception(f"Errore nel refresh token Microsoft: {resp.text}")
        return resp.json()