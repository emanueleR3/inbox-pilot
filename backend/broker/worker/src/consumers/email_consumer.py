import asyncio
import aiohttp
import json
from src.utils.broker_client import get_connection
from src.processors.message_processor import EmailProcessor

# Limita la concorrenza (evita di sovraccaricare API o risorse)
SEM = asyncio.Semaphore(10)

AUTOMATION_API_URL = "http://automations:8000/api/v1/process_email"  # TODO esempio

# Initialize the email processor
email_processor = EmailProcessor()

async def process_email(email_data):
    """
    Processa una singola email utilizzando la nuova architettura con filtering e DB save.
    """
    async with SEM:
        try:
            print(f"\n🎯 RABBITMQ - Messaggio ricevuto:")
            print("=" * 80)
            print(f"📧 Provider: {email_data.get('provider', 'N/A')}")
            print(f"📧 User: {email_data.get('user_email', 'N/A')}")
            print(f"📧 Da: {email_data.get('from', 'N/A')}")
            print(f"📧 A: {email_data.get('to', 'N/A')}")
            print(f"📧 Oggetto: {email_data.get('subject', 'N/A')}")
            print(f"📧 No Reply: {email_data.get('no_reply', False)}")
            print(f"📧 Is Sent: {email_data.get('is_sent', False)}")
            print(f"📧 Reply To ID: {email_data.get('reply_to_id', 'N/A')}")
            print(f"📧 Message ID: {email_data.get('message_id', 'N/A')}")
            print(f"📧 Thread ID: {email_data.get('original_thread_id', 'N/A')}")
            print(f"📧 Email type: {email_data.get('email_type', 'unknown')}")
            
            # Process through the new architecture
            result = await email_processor.process_message(email_data)
            
            if result:
                print(f"🔄 [PROCESSING] Result: {result}")
                
                if result.get('status') == 'thread_created':
                    print(f"🗂️ [THREAD] New thread created with ID: {result.get('thread_id')}")
                elif result.get('status') == 'ready_for_ai':
                    print(f"🤖 [AI] Message ready for AI processing")
                    # TODO: Route to AI workflow
            else:
                print(f"🚫 [PROCESSING] Message was filtered out or failed processing")
            
            # Debug: Show message body
            body = email_data.get('body_text', '')
            if body:
                print("\n📄 CORPO DEL MESSAGGIO:")
                print("-" * 40)
                # Mostra massimo 500 caratteri per non intasare i log
                if len(body) > 100:
                    print(f"{body[:100]}...")
                    print(f"[... troncato - lunghezza totale: {len(body)} caratteri]")
                else:
                    print(body)
                print("-" * 40)
            
            print("=" * 80)
            print(f"✅ [RabbitMQ] Email processata con successo!")
            
        except Exception as e:
            print(f"❌ Errore durante il processamento: {e}")

async def start_email_consumer():
    """
    Inizializza la connessione al broker e gestisce i messaggi in modalità asincrona.
    """
    connection, channel, queue = await get_connection()

    async with connection:
        print("🧠 Worker async in ascolto su 'emails_queue'...")

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process(ignore_processed=True):
                    try:
                        email_data = json.loads(message.body.decode())
                        asyncio.create_task(process_email(email_data))
                    except Exception as e:
                        print(f"❌ Errore nel parsing del messaggio: {e}")