import asyncio
from src.consumers.email_consumer import start_email_consumer

if __name__ == "__main__":
    asyncio.run(start_email_consumer())