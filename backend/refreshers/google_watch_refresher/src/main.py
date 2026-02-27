import asyncio
import os
from dotenv import load_dotenv
from src.watch_refresher import refresh_gmail_watches
from src.utils.logger import Logger

load_dotenv()

# Intervallo di refresh in ore (default: 24h)
REFRESH_INTERVAL_HOURS = int(os.getenv("REFRESH_INTERVAL_HOURS_WATCH", 24))


async def main():
    while True:
        Logger.log_info("### GOOGLE WATCH 🔁 Controllo watch Gmail da rinnovare...")
        await refresh_gmail_watches()
        Logger.log_info(
            f"### GOOGLE WATCH 💤 Attesa di {REFRESH_INTERVAL_HOURS} ore "
            f"prima del prossimo controllo..."
        )
        await asyncio.sleep(REFRESH_INTERVAL_HOURS * 3600)


if __name__ == "__main__":
    asyncio.run(main())
