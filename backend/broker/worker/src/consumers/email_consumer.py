import asyncio
import aiohttp
import json
from src.utils.broker_client import get_connection

# Limita la concorrenza (evita di sovraccaricare API o risorse)
SEM = asyncio.Semaphore(10)

AUTOMATION_API_URL = "http://automations:8000/api/v1/process_email"  # TODO esempio

async def process_email(email_data):
    """
    Processa una singola email chiamando il backend AI.
    """
    async with SEM:
        async with aiohttp.ClientSession() as session:
            try:
                # TODO chiamare il backend AI - all'interno di email_data c'è anche l'id dell'allegato eventualmente da prendere con una get di google
                async with session.post(AUTOMATION_API_URL, json=email_data, timeout=120) as resp:
                    if resp.status == 200:
                        print(f"✅ Elaborata email {email_data.get('id')}")
                    else:
                        print(f"⚠️ Errore nell'elaborazione {email_data.get('id')}: {resp.status}")
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