import asyncio
from dotenv import load_dotenv
from src.subscription_refresher import refresh_expiring_subscriptions
from src.utils.logger import Logger
import os

load_dotenv()

REFRESH_INTERVAL_MINUTES = int(os.getenv("REFRESH_INTERVAL_MINUTES_TOKENS", 15))

async def main():
    while True:
        Logger.log_info("### MICROSOFT SUBSCRIPTIONS 🔁 Controllo subscription Microsoft in scadenza...")
        await refresh_expiring_subscriptions()
        Logger.log_info(f"### MICROSOFT SUBSCRIPTIONS 💤 Attesa di {REFRESH_INTERVAL_MINUTES} ore prima del prossimo controllo...")
        await asyncio.sleep(REFRESH_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    asyncio.run(main())