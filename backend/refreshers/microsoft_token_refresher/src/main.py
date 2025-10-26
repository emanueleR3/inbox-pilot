import asyncio
import os
from dotenv import load_dotenv
from src.token_refresher import refresh_microsoft_tokens
from src.utils.logger import Logger

load_dotenv()

REFRESH_INTERVAL_MINUTES = int(os.getenv("REFRESH_INTERVAL_MINUTES_TOKENS", 15))

async def main():
    while True:
        Logger.log_info("### MICROSOFT 🔁 Controllo token Microsoft in scadenza...")
        await refresh_microsoft_tokens()
        Logger.log_info(f"### MICROSOFT 💤 Attesa di {REFRESH_INTERVAL_MINUTES} minuti prima del prossimo controllo...")
        await asyncio.sleep(REFRESH_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    asyncio.run(main())