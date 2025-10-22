import os
import json
import asyncio
from google.cloud import pubsub_v1
from google.oauth2 import service_account
from dotenv import load_dotenv
from src.utils.pubsub_handler import process_pubsub_message

load_dotenv()

# TODO quando leggo una mail forse devo aggiornare lo historyId nel DB?

SUBSCRIPTION_PATH = os.getenv("GOOGLE_PUBSUB_SUBSCRIPTION_PATH")
# Allow overriding via GOOGLE_CREDENTIALS_JSON as well, but prefer file path if provided
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or \
                          os.getenv("GOOGLE_CLOUD_CREDENTIALS") or \
                          os.getenv("GOOGLE_CREDENTIALS_PATH")
async def main():
    # Initialize Pub/Sub client with service account credentials
    if GOOGLE_CREDENTIALS_PATH:
        if os.path.exists(GOOGLE_CREDENTIALS_PATH):
            credentials = service_account.Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH)
            subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
        else:
            raise FileNotFoundError(
                f"Google credentials file not found at {GOOGLE_CREDENTIALS_PATH}. "
                f"Mount it into the container and set GOOGLE_APPLICATION_CREDENTIALS to that path."
            )
    else:
        # Fallback to default credentials (Application Default Credentials)
        print("Warning: Using default credentials. Set GOOGLE_APPLICATION_CREDENTIALS to a mounted service account file for production.")
        subscriber = pubsub_v1.SubscriberClient()

    # Get the running event loop
    loop = asyncio.get_running_loop()

    # Pub/Sub requires a synchronous callback; schedule async processing on the loop
    def callback(message):
        """
        Callback sincrona chiamata per ogni messaggio Pub/Sub. Pianifica l'elaborazione async.
        """
        try:
            data = json.loads(message.data)
            # Schedule the coroutine on the main loop in a thread-safe way
            loop.call_soon_threadsafe(asyncio.create_task, process_pubsub_message(data))
            message.ack()
        except Exception as e:
            print(f"Errore callback Pub/Sub: {e}")
            message.nack()

    streaming_pull_future = subscriber.subscribe(SUBSCRIPTION_PATH, callback=callback)
    print(f"### GOOGLE 📧 Listening for messages on {SUBSCRIPTION_PATH}...")

    # Mantieni vivo il listener
    try:
        await loop.run_in_executor(None, streaming_pull_future.result)
    except KeyboardInterrupt:
        streaming_pull_future.cancel()

if __name__ == "__main__":
    asyncio.run(main())