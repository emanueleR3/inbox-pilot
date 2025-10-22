from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
import asyncio
from src.graph_fetcher import fetch_new_message
from src.utils.broker_publisher import publish_to_broker
from src.utils.logger import log_info, log_error

app = FastAPI()

@app.get("/microsoft/webhook")
async def verify_microsoft_subscription(validationToken: str = None):
    """
    Endpoint di verifica della subscription Microsoft.
    Microsoft invia GET con validationToken la prima volta per verificare l'endpoint.
    """
    if validationToken:
        log_info(f"🔐 MICROSOFT - Verifica subscription con validationToken: {validationToken[:20]}...")
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
        log_info(f"🔐 MICROSOFT - Verifica subscription POST con validationToken: {validation_token[:20]}...")
        return PlainTextResponse(validation_token)
    
    try:
        data = await request.json()
    except Exception as e:
        # Se il body è vuoto o non è JSON valido, ritorna OK
        # Questo può succedere durante i test di verifica di Microsoft
        log_info("⚠️ MICROSOFT - Ricevuta richiesta senza JSON valido (probabilmente test di verifica)")
        return JSONResponse({"status": "ok", "message": "No JSON data received"})
    
    notifications = data.get("value", [])
    log_info(f"🔔 MICROSOFT - Ricevute {len(notifications)} notifiche webhook")
    
    # Log del payload completo per debug
    log_info(f"🔍 MICROSOFT - Payload completo ricevuto: {data}")
    
    if not notifications:
        log_info("ℹ️ MICROSOFT - Nessuna notifica nel payload")
        return {"status": "ok"}

    tasks = []
    for i, notif in enumerate(notifications):
        # Log completo della notifica per capire la struttura
        log_info(f"🔍 MICROSOFT - Notifica {i+1} completa: {notif}")
        
        user_id = notif.get("userId")
        resource_data = notif.get("resourceData", {})
        message_id = resource_data.get("id")
        
        # Prova altri possibili campi per userId
        if not user_id:
            # Microsoft potrebbe usare altri campi per l'user ID
            user_id = notif.get("user_id") or notif.get("userPrincipalName") or notif.get("subscriptionId")
            log_info(f"� MICROSOFT - Tentativo alternativo userId: {user_id}")
        
        log_info(f"�📬 MICROSOFT - Notifica {i+1}/{len(notifications)}: userId={user_id}, messageId={message_id}")
        log_info(f"🔍 MICROSOFT - Tutti i campi disponibili: {list(notif.keys())}")
        log_info(f"🔍 MICROSOFT - ResourceData: {resource_data}")

        if message_id and user_id:
            # Recupera il messaggio completo via Graph API (async)
            tasks.append(asyncio.create_task(fetch_new_message(user_id, message_id)))
        else:
            log_error(f"❌ MICROSOFT - Notifica {i+1} incompleta: userId={user_id}, messageId={message_id}")
            log_error(f"❌ MICROSOFT - Campi mancanti - userId presente: {bool(user_id)}, messageId presente: {bool(message_id)}")

    if not tasks:
        log_info("⚠️ MICROSOFT - Nessun messaggio valido da recuperare")
        return {"status": "ok"}

    # Recupera tutte le mail in parallelo
    log_info(f"🔄 MICROSOFT - Avvio recupero di {len(tasks)} messaggi in parallelo...")
    messages = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filtra i messaggi validi (esclude le eccezioni)
    valid_messages = [msg for msg in messages if msg is not None and not isinstance(msg, Exception)]
    
    if valid_messages:
        log_info(f"📤 MICROSOFT - Invio di {len(valid_messages)} messaggi a RabbitMQ...")
        # Pubblica le mail sul broker RabbitMQ
        await publish_to_broker(valid_messages)
        log_info(f"✅ MICROSOFT - {len(valid_messages)} messaggi inviati con successo a RabbitMQ")
    else:
        log_info("⚠️ MICROSOFT - Nessun messaggio valido da inviare a RabbitMQ")

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("### MICROSOFT 📧 Starting Microsoft listener on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)