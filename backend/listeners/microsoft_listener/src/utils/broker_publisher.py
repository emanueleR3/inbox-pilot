import aio_pika
import json
import os
from dotenv import load_dotenv
from .logger import log_info, log_error

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
QUEUE_NAME = os.getenv("IMAP_QUEUE_NAME", "emails_queue")

async def publish_to_broker(messages):
    """
    Pubblica i messaggi su RabbitMQ con logging dettagliato.
    """
    if not messages:
        log_info("📤 BROKER - Nessun messaggio da pubblicare")
        return
    
    # Filtra i messaggi None
    valid_messages = [msg for msg in messages if msg is not None]
    
    if not valid_messages:
        log_info("📤 BROKER - Tutti i messaggi sono None, niente da pubblicare")
        return
    
    try:
        log_info(f"🔌 BROKER - Connessione a RabbitMQ: {RABBITMQ_URL}")
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        await channel.declare_queue(QUEUE_NAME, durable=True)
        
        log_info(f"📤 BROKER - Pubblicazione di {len(valid_messages)} messaggi su coda '{QUEUE_NAME}'")

        for i, msg in enumerate(valid_messages):
            try:
                message_body = json.dumps(msg).encode()
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=message_body,
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                    ),
                    routing_key=QUEUE_NAME,
                )
                
                # Log informazioni del messaggio pubblicato
                subject = msg.get('subject', 'No subject')[:50]
                from_addr = msg.get('from', 'Unknown sender')[:50]
                log_info(f"✅ BROKER - Messaggio {i+1}/{len(valid_messages)} pubblicato: '{subject}' da '{from_addr}'")
                
            except Exception as e:
                log_error(f"❌ BROKER - Errore pubblicazione messaggio {i+1}: {str(e)}", e)

        await connection.close()
        log_info(f"🎯 BROKER - Pubblicazione completata! {len(valid_messages)} messaggi inviati con successo")
        
    except Exception as e:
        log_error(f"❌ BROKER - Errore connessione/pubblicazione RabbitMQ: {str(e)}", e)