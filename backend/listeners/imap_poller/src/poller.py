import asyncio
import os
from dotenv import load_dotenv
from src.imap_client import ImapClient
from src.db_client import get_all_imap_accounts
from src.utils.logger import log_info, log_error
from src.broker_client import RabbitMQPublisher

load_dotenv()

MAX_CONCURRENT_CONNECTIONS = int(os.getenv("MAX_CONCURRENT_CONNECTIONS_IMAP", 10))   # Limite per scalabilità
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES_IMAP", 2))              # Ogni quanti minuti controllare le mail

publisher = RabbitMQPublisher()

async def poll_account(account):
    try:
        client = ImapClient(
            host=account["imap_host"],
            port=account["imap_port"],
            username=account["email"],
            password=account["password"],
            use_ssl=account["use_ssl"]
        )
        client.connect()
        new_mails = client.fetch_unseen_messages()

        for mail in new_mails:
            log_info(f"📩 Nuova mail da {mail['from']} per {account['email']} | {mail['subject']}")        
            
            message_payload = {
                "provider": "imap",
                "user_email": account["email"],  # Cambiato da "account" a "user_email" per consistenza con il broker
                "mail_id": mail["id"],
                "message_id": mail["message_id"],
                "thread_id": mail["thread_id"],
                "from": mail["from"],
                "to": mail["to"],
                "cc": mail["cc"],
                "bcc": mail["bcc"],
                "subject": mail["subject"],
                "date": mail["date"],
                "timestamp": mail["timestamp"],
                "body_text": mail["body_text"],
                "body_html": mail["body_html"],
                "content_type": mail["content_type"],
                "charset": mail["charset"],
                "size": mail["size"],
                "raw": mail["raw"].decode(errors="ignore"),
                "subscription_id": account.get("subscription_id")  # Aggiunge riferimento alla subscription
            }

            await publisher.publish_message(message_payload)

            client.mark_as_seen(mail["id"])

        client.close()

    except Exception as e:
        log_error(f"Errore nel polling IMAP per {account['email']}: {e}")

async def poll_all_accounts():
    accounts = await get_all_imap_accounts()
    sem = asyncio.Semaphore(MAX_CONCURRENT_CONNECTIONS)

    async def sem_task(account):
        async with sem:
            await poll_account(account)

    await asyncio.gather(*(sem_task(acc) for acc in accounts))