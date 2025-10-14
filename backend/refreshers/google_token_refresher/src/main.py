import asyncio
import os
from dotenv import load_dotenv
from src.token_refresher import refresh_google_tokens

load_dotenv()

REFRESH_INTERVAL_MINUTES = os.getenv("REFRESH_INTERVAL_MINUTES_TOKENS", 15)

async def main():
    while True:
        print("🔁 Controllo token Google in scadenza...")
        await refresh_google_tokens()
        print(f"💤 Attesa di {REFRESH_INTERVAL_MINUTES} minuti per il prossimo controllo...")
        await asyncio.sleep(REFRESH_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    asyncio.run(main())