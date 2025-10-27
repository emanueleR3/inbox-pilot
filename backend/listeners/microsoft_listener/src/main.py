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
        
        # Controlla se è una richiesta di validazione nel body
        # Durante il rinnovo, Microsoft potrebbe inviare il validationToken nel body
        if isinstance(data, dict) and "validationToken" in data:
            validation_token = data["validationToken"]
            log_info(f"🔐 MICROSOFT - Verifica subscription POST con validationToken nel body: {validation_token[:20]}...")
            return PlainTextResponse(validation_token)
            
    except Exception as e:
        # Se il body è vuoto o non è JSON valido, ritorna OK
        # Questo può succedere durante i test di verifica di Microsoft
        log_info("⚠️ MICROSOFT - Ricevuta richiesta senza JSON valido (probabilmente test di verifica)")
        return JSONResponse({"status": "ok", "message": "No JSON data received"})
    
    notifications = data.get("value", [])
    log_info(f"🔔 MICROSOFT - Ricevute {len(notifications)} notifiche webhook")
    
    if not notifications:
        log_info("ℹ️ MICROSOFT - Nessuna notifica nel payload")
        return {"status": "ok"}

    tasks = []
    for i, notif in enumerate(notifications):
        
        # Estrai subscriptionId e dati del messaggio
        subscription_id = notif.get("subscriptionId")
        resource_data = notif.get("resourceData", {})
        message_id = resource_data.get("id")
        
        # Estrai anche l'userId dal campo resource (formato: Users/{userId}/Messages/{messageId})
        resource_path = notif.get("resource", "")
        actual_user_id = None
        if resource_path and "Users/" in resource_path:
            # Estrai l'userId dal percorso resource: Users/2757a1285292fcf7/Messages/...
            parts = resource_path.split("/")
            if len(parts) >= 2 and parts[0] == "Users":
                actual_user_id = parts[1]

        if message_id and subscription_id and actual_user_id:
            # Usa il subscription_id per recuperare le credenziali e actual_user_id per l'API Graph
            log_info(f"📧 MICROSOFT - Recupero messaggio {message_id} per subscription {subscription_id}, user {actual_user_id}")
            tasks.append(asyncio.create_task(fetch_new_message(subscription_id, message_id, actual_user_id)))
        else:
            log_error(f"❌ MICROSOFT - Notifica {i+1} incompleta: subscriptionId={subscription_id}, actualUserId={actual_user_id}, messageId={message_id}")
            log_error(f"❌ MICROSOFT - Campi mancanti - subscriptionId presente: {bool(subscription_id)}, actualUserId presente: {bool(actual_user_id)}, messageId presente: {bool(message_id)}")
            # Log della notifica completa per debug
            log_error(f"❌ MICROSOFT - Notifica completa: {notif}")
 
    if not tasks:
        log_info("⚠️ MICROSOFT - Nessun messaggio valido da recuperare")
        return {"status": "ok"}

    # Recupera tutte le mail in parallelo
    messages = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Analizza i risultati per logging dettagliato
    valid_messages = []
    exceptions_count = 0
    
    for i, msg in enumerate(messages):
        if isinstance(msg, Exception):
            exceptions_count += 1
            log_error(f"❌ MICROSOFT - Errore nel task {i+1}: {type(msg).__name__}: {str(msg)}")
        elif msg is not None:
            valid_messages.append(msg)
    
    if exceptions_count > 0:
        log_error(f"❌ MICROSOFT - {exceptions_count} errori su {len(messages)} tentativi di recupero messaggi")
    
    if valid_messages:
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