import httpx
from src.db_client import get_user_credentials

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

async def fetch_new_message(user_id: str, message_id: str):
    """
    Recupera la mail completa tramite Microsoft Graph.
    """
    # Recupera access token dal DB per l'utente
    access_token = await get_user_credentials(user_id).get("access_token")

    url = f"{GRAPH_BASE_URL}/users/{user_id}/messages/{message_id}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
        resp.raise_for_status()
        return resp.json()