from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
import asyncio
from src.graph_fetcher import fetch_new_message
from src.utils.broker_publisher import publish_to_broker
from src.utils.logger import log_info, log_error
from src.db_client import get_subscription_type

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
    subscription_types = {}  # Cache per i tipi di subscription
    
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
            # Determina il tipo di subscription (inbound o outbound)
            try:
                if subscription_id not in subscription_types:
                    subscription_types[subscription_id] = await get_subscription_type(subscription_id)
                
                is_outbound = subscription_types[subscription_id] == "outbound"
                
                # Usa il subscription_id per recuperare le credenziali e actual_user_id per l'API Graph
                tasks.append(asyncio.create_task(
                    fetch_new_message(subscription_id, message_id, actual_user_id, is_outbound)
                ))
            except Exception as e:
                log_error(f"❌ MICROSOFT - Errore nel determinare il tipo di subscription {subscription_id}: {str(e)}")
        else:
            log_error(f"❌ MICROSOFT - Notifica {i+1} incompleta: subscriptionId={subscription_id}, actualUserId={actual_user_id}, messageId={message_id}")
 
    if not tasks:
        log_info("⚠️ MICROSOFT - Nessun messaggio valido da recuperare")
        return {"status": "ok"}

    # Recupera tutte le mail in parallelo
    messages = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Analizza i risultati per logging dettagliato
    valid_messages = []
    orphan_errors = 0
    other_errors = 0
    
    for i, msg in enumerate(messages):
        if isinstance(msg, Exception):
            error_str = str(msg)
            if "non trovato" in error_str:
                orphan_errors += 1
            else:
                other_errors += 1
                log_error(f"❌ MICROSOFT - Errore nel task {i+1}: {type(msg).__name__}: {error_str}")
        elif msg is not None:
            valid_messages.append(msg)
    
    if orphan_errors > 0:
        log_error(f"❌ MICROSOFT - {orphan_errors} subscription orfane rilevate (verranno pulite automaticamente)")
    if other_errors > 0:
        log_error(f"❌ MICROSOFT - {other_errors} altri errori su {len(messages)} tentativi")
    
    if valid_messages:
        # Invia TUTTI i messaggi al broker RabbitMQ (sia inbound che outbound)
        await publish_to_broker(valid_messages)
        
        # Separa i messaggi per logging
        inbound_messages = [msg for msg in valid_messages if not msg.get('is_sent', False)]
        outbound_messages = [msg for msg in valid_messages if msg.get('is_sent', False)]
        
        log_info(f"✅ MICROSOFT - {len(valid_messages)} messaggi totali inviati al broker RabbitMQ")
        if inbound_messages:
            log_info(f"   📥 {len(inbound_messages)} messaggi INBOUND")
        if outbound_messages:
            log_info(f"   � {len(outbound_messages)} messaggi OUTBOUND")
        
        total_processed = len(inbound_messages) + len(outbound_messages)
        log_info(f"✅ MICROSOFT - Totale messaggi processati: {total_processed}")
    else:
        log_info("⚠️ MICROSOFT - Nessun messaggio valido da processare")

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("### MICROSOFT 📧 Starting Microsoft listener on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)