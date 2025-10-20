from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
import asyncio
from src.graph_fetcher import fetch_new_message
from src.utils.broker_publisher import publish_to_broker

app = FastAPI()

@app.get("/microsoft/webhook")
async def verify_microsoft_subscription(validationToken: str = None):
    """
    Endpoint di verifica della subscription Microsoft.
    Microsoft invia GET con validationToken la prima volta per verificare l'endpoint.
    """
    if validationToken:
        return PlainTextResponse(validationToken)
    return PlainTextResponse("OK")

@app.post("/microsoft/webhook")
async def receive_microsoft_notification(request: Request):
    """
    Endpoint per ricevere notifiche da Microsoft Graph.
    """
    # Controlla se è una richiesta di verifica (validationToken come query param)
    validation_token = request.query_params.get("validationToken")
    if validation_token:
        # Durante la verifica, Microsoft si aspetta solo il token come risposta
        return PlainTextResponse(validation_token)
    
    try:
        data = await request.json()
    except Exception as e:
        # Se il body è vuoto o non è JSON valido, ritorna OK
        # Questo può succedere durante i test di verifica di Microsoft
        return JSONResponse({"status": "ok", "message": "No JSON data received"})
    
    notifications = data.get("value", [])

    tasks = []
    for notif in notifications:
        user_id = notif.get("userId")
        message_id = notif.get("resourceData", {}).get("id")

        if message_id and user_id:
            # Recupera il messaggio completo via Graph API (async)
            tasks.append(asyncio.create_task(fetch_new_message(user_id, message_id)))

    # Recupera tutte le mail in parallelo
    messages = await asyncio.gather(*tasks)

    # Pubblica le mail sul broker RabbitMQ
    await publish_to_broker(messages)

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Microsoft listener on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)