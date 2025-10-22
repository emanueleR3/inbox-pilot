import asyncio
import aiohttp
import json
from src.utils.broker_client import get_connection

# Limita la concorrenza (evita di sovraccaricare API o risorse)
SEM = asyncio.Semaphore(10)

AUTOMATION_API_URL = "http://automations:8000/api/v1/process_email"  # TODO esempio

async def process_email(email_data):
    """
    Processa una singola email - MODALITÀ DEBUG: stampa il messaggio.
    """
    async with SEM:
        try:
            print(f"\n🎯 RABBITMQ - Messaggio ricevuto e processato:")
            print("=" * 80)
            print(f"📧 Provider: {email_data.get('provider', 'N/A')}")
            print(f"📧 User: {email_data.get('user_email', 'N/A')}")
            print(f"📧 Da: {email_data.get('from', 'N/A')}")
            print(f"📧 A: {email_data.get('to', 'N/A')}")
            print(f"📧 Oggetto: {email_data.get('subject', 'N/A')}")
            print(f"📧 Data: {email_data.get('date', 'N/A')}")
            print(f"📧 Thread ID: {email_data.get('thread_id', 'N/A')}")
            print(f"📧 Message ID: {email_data.get('message_id', 'N/A')}")
            print(f"📧 Labels: {', '.join(email_data.get('labels', []))}")
            
            body = email_data.get('body_text', '')
            if body:
                print("\n📄 CORPO DEL MESSAGGIO:")
                print("-" * 40)
                # Mostra massimo 500 caratteri per non intasare i log
                if len(body) > 500:
                    print(f"{body[:500]}...")
                    print(f"[... troncato - lunghezza totale: {len(body)} caratteri]")
                else:
                    print(body)
                print("-" * 40)
            
            print(f"📧 Timestamp: {email_data.get('timestamp', 'N/A')}")
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