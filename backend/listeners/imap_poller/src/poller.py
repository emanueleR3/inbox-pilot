import asyncio
import os
from dotenv import load_dotenv
from src.imap_client import ImapClient
from src.db_client import get_all_imap_accounts, get_last_sent_message_info, update_last_sent_message_info, get_last_received_message_info, update_last_received_message_info
from src.utils.logger import log_info, log_error
from src.broker_client import RabbitMQPublisher

load_dotenv()

MAX_CONCURRENT_CONNECTIONS = int(os.getenv("MAX_CONCURRENT_CONNECTIONS_IMAP", 10))   # Limite per scalabilità
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES_IMAP", 2))              # Ogni quanti minuti controllare le mail

publisher = RabbitMQPublisher()

async def poll_account_inbound(account):
    """
    Controlla i messaggi ricevuti per un singolo account IMAP con tracking basato su timestamp.
    Implementa la logica di primo polling: se è il primo polling, imposta solo la baseline senza inviare messaggi.
    """
    try:
        email = account["email"]
        
        # Recupera info sull'ultimo messaggio ricevuto processato
        last_received_info = get_last_received_message_info(email)
        last_timestamp = last_received_info.get("timestamp")
        last_message_id = last_received_info.get("message_id")
        
        is_first_polling = last_timestamp is None and last_message_id is None
        
        # Crea client IMAP
        client = ImapClient(
            host=account["imap_host"],
            port=account["imap_port"],
            username=email,
            password=account["password"],
            use_ssl=account["use_ssl"]
        )
        
        # Connessione
        client.connect()
        
        # Recupera messaggi ricevuti
        received_messages = client.fetch_received_messages_since(last_timestamp, is_first_polling, last_message_id)
        
        if received_messages:
            # Ordina per timestamp per processare dal più vecchio al più recente
            received_messages.sort(key=lambda x: x.get("timestamp", ""))
            
            latest_message = None
            
            for message in received_messages:
                # Se NON è il primo polling, invia al broker
                if not is_first_polling:
                    log_info("   💌 Messaggio inbound IMAP - inviato al broker")
                    
                    # Importa le funzioni per controllare no-reply e sent
                    from src.utils.mail_parser import is_no_reply_email, is_sent_message
                    
                    message_payload = {
                        "provider": "imap",
                        "user_email": email,
                        "mail_id": message["id"],
                        "message_id": message["message_id"],
                        "reply_to_id": message["reply_to_id"],
                        "from": message["from"],
                        "to": message["to"],
                        "cc": message["cc"],
                        "bcc": message["bcc"],
                        "subject": message["subject"],
                        "date": message["date"],
                        "timestamp": message["timestamp"],
                        "body_text": message["body_text"],
                        "body_html": message["body_html"],
                        "content_type": message["content_type"],
                        "charset": message["charset"],
                        "size": message["size"],
                        "raw": message["raw"].decode(errors="ignore"),
                        "subscription_id": account.get("subscription_id"),
                        "folder_type": "inbox",
                        "no_reply": is_no_reply_email(message.get("from", "")),
                        "is_sent": is_sent_message(message.get("from", ""), email, "inbox"),
                    }

                    await publisher.publish_message(message_payload)
                else:
                    log_info("   🔄 Primo polling - messaggio usato solo per baseline")

                latest_message = message
            
            # Aggiorna il timestamp dell'ultimo messaggio processato
            if latest_message:
                update_last_received_message_info(
                    email,
                    latest_message.get("message_id", ""),
                    latest_message.get("timestamp", "")
                )
                
        elif is_first_polling:
            # Primo polling senza messaggi negli ultimi 2 minuti
            # Imposta il messaggio più recente come baseline
            recent_message = client.get_most_recent_received_message()
            
            if recent_message:
                update_last_received_message_info(
                    email,
                    recent_message.get("message_id", ""),
                    recent_message.get("timestamp", "")
                )
        else:
            log_info(f"📩 Nessun nuovo messaggio ricevuto per {email}")
        
        # Chiudi connessione
        client.close()
        
    except Exception as e:
        log_error(f"❌ Errore nel polling messaggi ricevuti per {account.get('email', 'unknown')}: {str(e)}")

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
        
        # Processa messaggi in arrivo (INBOX)
        new_mails = client.fetch_unseen_messages("INBOX")
        for mail in new_mails:
            log_info(f"📩 Nuova mail INBOUND da {mail['from']} per {account['email']} | {mail['subject']}")        
            
            # Importa le funzioni per controllare no-reply e sent
            from src.utils.mail_parser import is_no_reply_email, is_sent_message
            
            message_payload = {
                "provider": "imap",
                "user_email": account["email"],  # Cambiato da "account" a "user_email" per consistenza con il broker
                "mail_id": mail["id"],
                "message_id": mail["message_id"],
                "reply_to_id": mail["reply_to_id"],
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
                "subscription_id": account.get("subscription_id"),  # Aggiunge riferimento alla subscription
                "folder_type": "inbox",  # Indica che è un messaggio in arrivo
                "no_reply": is_no_reply_email(mail.get("from", "")),
                "is_sent": is_sent_message(mail.get("from", ""), account["email"], "inbox"),
            }

            await publisher.publish_message(message_payload)
            client.mark_as_seen(mail["id"])

        # Processa messaggi inviati (Sent folder) - ora invia al broker tramite poll_account_outbound
        # La logica è stata spostata nella funzione poll_account_outbound
        # che viene chiamata separatamente per gestire il tracking dei timestamp

        client.close()

    except Exception as e:
        log_error(f"Errore nel polling IMAP per {account['email']}: {e}")

async def poll_account_outbound(account):
    """
    Controlla i messaggi inviati per un singolo account IMAP.
    Implementa la logica di primo polling con soglia di 2 minuti.
    """
    try:
        email = account["email"]
        
        # Recupera info sull'ultimo messaggio inviato processato
        last_sent_info = get_last_sent_message_info(email)
        last_timestamp = last_sent_info.get("timestamp")
        last_message_id = last_sent_info.get("message_id")
        
        is_first_polling = last_timestamp is None and last_message_id is None
        
        # Crea client IMAP
        client = ImapClient(
            host=account["imap_host"],
            port=account["imap_port"],
            username=email,
            password=account["password"],
            use_ssl=account["use_ssl"]
        )
        
        # Connessione
        client.connect()
        
        # Recupera messaggi inviati
        sent_messages = client.fetch_sent_messages_since(last_timestamp, is_first_polling, last_message_id)
        
        if sent_messages:
            # Ordina per timestamp per processare dal più vecchio al più recente
            sent_messages.sort(key=lambda x: x.get("timestamp", ""))
            
            latest_message = None
            
            for message in sent_messages:
                # Se NON è il primo polling, invia al broker
                if not is_first_polling:
                    log_info("   📤 Messaggio outbound IMAP - inviato al broker")
                    
                    # Importa le funzioni per controllare no-reply e sent
                    from src.utils.mail_parser import is_no_reply_email, is_sent_message
                    
                    message_payload = {
                        "provider": "imap",
                        "user_email": email,
                        "mail_id": message["id"],
                        "message_id": message["message_id"],
                        "reply_to_id": message["reply_to_id"],
                        "from": message["from"],
                        "to": message["to"],
                        "cc": message["cc"],
                        "bcc": message["bcc"],
                        "subject": message["subject"],
                        "date": message["date"],
                        "timestamp": message["timestamp"],
                        "body_text": message["body_text"],
                        "body_html": message["body_html"],
                        "content_type": message["content_type"],
                        "charset": message["charset"],
                        "size": message["size"],
                        "raw": message["raw"].decode(errors="ignore"),
                        "subscription_id": account.get("subscription_id"),
                        "folder_type": "sent",
                        "no_reply": is_no_reply_email(message.get("from", "")),
                        "is_sent": is_sent_message(message.get("from", ""), email, "sent"),
                    }

                    await publisher.publish_message(message_payload)
                else:
                    log_info("   🔄 Primo polling - messaggio usato solo per baseline")

                latest_message = message
            
            # Aggiorna il timestamp dell'ultimo messaggio processato
            if latest_message:
                update_last_sent_message_info(
                    email,
                    latest_message.get("message_id", ""),
                    latest_message.get("timestamp", "")
                )
                
        elif is_first_polling:
            # Primo polling senza messaggi negli ultimi 2 minuti
            # Imposta il messaggio più recente come baseline
            recent_message = client.get_most_recent_sent_message()
            
            if recent_message:
                update_last_sent_message_info(
                    email,
                    recent_message.get("message_id", ""),
                    recent_message.get("timestamp", "")
                )
        else:
            log_info(f"📤 Nessun nuovo messaggio inviato per {email}")
        
        # Chiudi connessione
        client.close()
        
    except Exception as e:
        log_error(f"❌ Errore nel polling messaggi inviati per {account.get('email', 'unknown')}: {str(e)}")

async def poll_all_accounts():
    accounts = await get_all_imap_accounts()
    sem = asyncio.Semaphore(MAX_CONCURRENT_CONNECTIONS)

    async def sem_task_inbound(account):
        async with sem:
            await poll_account_inbound(account)
    
    async def sem_task_outbound(account):
        async with sem:
            await poll_account_outbound(account)

    # Crea task per entrambi i tipi di polling
    tasks = []
    for acc in accounts:
        tasks.append(sem_task_inbound(acc))   # Messaggi in arrivo (nuova logica)
        tasks.append(sem_task_outbound(acc))  # Messaggi inviati
    
    # Esegue tutti i task concorrentemente
    await asyncio.gather(*tasks)