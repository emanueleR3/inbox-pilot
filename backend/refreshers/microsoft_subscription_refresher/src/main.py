import asyncio
from dotenv import load_dotenv
from src.subscription_refresher import refresh_expiring_subscriptions
import os

load_dotenv()

REFRESH_INTERVAL_HOURS = os.getenv("REFRESH_INTERVAL_HOURS_SUBSCRIPTIONS", 3)

async def main():
    while True:
        print("🔁 Controllo subscription in scadenza...")
        await refresh_expiring_subscriptions()
        print(f"💤 Attesa di {REFRESH_INTERVAL_HOURS} ore per il prossimo ciclo...")
        await asyncio.sleep(REFRESH_INTERVAL_HOURS * 3600)

if __name__ == "__main__":
    asyncio.run(main())