import os
import json
import asyncio
from google.cloud import pubsub_v1
from dotenv import load_dotenv
from src.utils.pubsub_handler import process_pubsub_message

load_dotenv()

SUBSCRIPTION_PATH = os.getenv("GOOGLE_PUBSUB_SUBSCRIPTION_PATH")

async def callback(message):
    """
    Callback async chiamata per ogni messaggio Pub/Sub
    """
    try:
        data = json.loads(message.data)
        # Lancia task async, così il loop non blocca altri messaggi
        asyncio.create_task(process_pubsub_message(data))
        message.ack()
    except Exception as e:
        print(f"Errore callback Pub/Sub: {e}")
        message.nack()


async def main():
    subscriber = pubsub_v1.SubscriberClient()

    streaming_pull_future = subscriber.subscribe(SUBSCRIPTION_PATH, callback=callback)
    print(f"Listening for messages on {SUBSCRIPTION_PATH}...")

    # Mantieni vivo il listener
    try:
        await asyncio.get_event_loop().run_in_executor(None, streaming_pull_future.result)
    except KeyboardInterrupt:
        streaming_pull_future.cancel()

if __name__ == "__main__":
    asyncio.run(main())