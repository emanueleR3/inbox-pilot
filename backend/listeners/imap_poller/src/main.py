import os
from dotenv import load_dotenv
import asyncio
from src.poller import poll_all_accounts, publisher
from src.utils.logger import log_info

load_dotenv()

POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES_IMAP", 1))

async def main():
    await publisher.connect()  # connessione RabbitMQ globale
    log_info("🔗 Listener IMAP connesso al broker")

    while True:
        print("### IMAP 📧 Avvio polling IMAP per tutte le caselle (INBOX + Sent)...")
        await poll_all_accounts()
        print(f"### IMAP 💤 Attesa di {POLL_INTERVAL_MINUTES} minuti per il prossimo ciclo...")
        await asyncio.sleep(POLL_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    asyncio.run(main())