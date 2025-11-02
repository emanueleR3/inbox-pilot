import asyncio
import os
from dotenv import load_dotenv
from src.imap_client import ImapClient
from src.db_client import get_all_imap_accounts, get_last_sent_message_info, update_last_sent_message_info
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
        
        # Processa messaggi in arrivo (INBOX)
        new_mails = client.fetch_unseen_messages("INBOX")
        for mail in new_mails:
            log_info(f"📩 Nuova mail INBOUND da {mail['from']} per {account['email']} | {mail['subject']}")        
            
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
                "subscription_id": account.get("subscription_id"),  # Aggiunge riferimento alla subscription
                "folder_type": "inbox"  # Indica che è un messaggio in arrivo
            }

            await publisher.publish_message(message_payload)
            client.mark_as_seen(mail["id"])

        # Processa messaggi inviati (Sent folder) - solo log, non invia al broker
        sent_mails = client.fetch_sent_messages()
        for mail in sent_mails:
            log_info(f"📤 OUTBOUND MAIL (solo log) da {account['email']} a {mail['to']} | {mail['subject']}")
            log_info(f"   📧 Da: {mail['from']}")
            log_info(f"   📧 A: {mail['to']}")
            log_info(f"   📅 Data: {mail['date']}")
            log_info(f"   📝 Oggetto: {mail['subject']}")
            log_info(f"   📄 Corpo (primi 200 char): {mail['body_text'][:200]}...")
            log_info(f"   🆔 Message ID: {mail['message_id']}")
            log_info(f"   🔗 Thread ID: {mail['thread_id']}")
            log_info(f"   📊 Dimensione: {mail['size']} bytes")
            log_info("   💡 Messaggio outbound IMAP non inviato al broker (solo monitoraggio)")
            
            # Marca come letto anche le email inviate per evitare di riprocessarle
            client.mark_as_seen(mail["id"])

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
        
        if is_first_polling:
            log_info(f"📤 PRIMO POLLING per {email} - cerco messaggi degli ultimi 2 minuti")
        else:
            log_info(f"📤 Polling incrementale per {email} (ultimo: {last_timestamp})")
        
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
            log_info(f"📤 Trovati {len(sent_messages)} nuovi messaggi inviati per {email}")
            
            # Ordina per timestamp per processare dal più vecchio al più recente
            sent_messages.sort(key=lambda x: x.get("timestamp", ""))
            
            latest_message = None
            
            for message in sent_messages:
                # Log dettagliato del messaggio inviato (non inviare al broker)
                log_info("="*80)
                log_info("📤 IMAP OUTBOUND - Messaggio inviato rilevato:")
                log_info(f"   📧 Account: {email}")
                log_info(f"   📧 Da: {message.get('from')}")
                log_info(f"   📧 A: {message.get('to')}")
                if message.get('cc'):
                    log_info(f"   📧 CC: {message.get('cc')}")
                log_info(f"   📧 Oggetto: {message.get('subject')}")
                log_info(f"   📧 Data: {message.get('date')}")
                log_info(f"   📧 Message-ID: {message.get('message_id')}")
                log_info(f"   📧 Thread-ID: {message.get('thread_id')}")
                log_info(f"   📧 Cartella: {message.get('folder')}")
                log_info(f"   📊 Dimensione: {message.get('size')} bytes")
                
                # Mostra un'anteprima del corpo (primi 150 caratteri)
                body_preview = message.get('body_text', '')[:150]
                if len(body_preview) >= 150:
                    body_preview += "..."
                log_info(f"   📄 Anteprima corpo: {body_preview}")
                log_info("   💡 Messaggio outbound IMAP - non inviato al broker (solo monitoraggio)")
                log_info("="*80)
                
                latest_message = message
            
            # Aggiorna il timestamp dell'ultimo messaggio processato
            if latest_message:
                update_last_sent_message_info(
                    email,
                    latest_message.get("message_id", ""),
                    latest_message.get("timestamp", "")
                )
                log_info(f"✅ Aggiornato tracking per {email}: ultimo messaggio {latest_message.get('message_id')}")
                
        elif is_first_polling:
            # Primo polling senza messaggi negli ultimi 2 minuti
            # Imposta il messaggio più recente come baseline
            log_info(f"📤 Primo polling per {email}: nessun messaggio negli ultimi 2 minuti")
            log_info(f"📤 Cerco il messaggio più recente per impostare baseline...")
            
            most_recent = client.get_most_recent_sent_message()
            if most_recent:
                update_last_sent_message_info(
                    email,
                    most_recent.get("message_id", ""),
                    most_recent.get("timestamp", "")
                )
                log_info(f"✅ Baseline impostata per {email}: {most_recent.get('message_id')} ({most_recent.get('date')})")
            else:
                log_info(f"📤 Nessun messaggio recente trovato per {email} - baseline rimarrà null")
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
            await poll_account(account)
    
    async def sem_task_outbound(account):
        async with sem:
            await poll_account_outbound(account)

    # Crea task per entrambi i tipi di polling
    tasks = []
    for acc in accounts:
        tasks.append(sem_task_inbound(acc))  # Messaggi in arrivo
        tasks.append(sem_task_outbound(acc))  # Messaggi inviati
    
    # Esegue tutti i task concorrentemente
    await asyncio.gather(*tasks)