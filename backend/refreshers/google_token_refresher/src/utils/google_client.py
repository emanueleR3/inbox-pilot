import httpx
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

async def refresh_google_token(refresh_token: str):
    """
    Usa il refresh_token per ottenere un nuovo access_token da Google.
    """
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=data)
        if resp.status_code != 200:
            raise Exception(f"Errore nel refresh del token Google: {resp.text}")
        return resp.json()