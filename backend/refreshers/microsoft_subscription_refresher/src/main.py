import asyncio
from dotenv import load_dotenv
from src.subscription_refresher import refresh_expiring_subscriptions, cleanup_all_orphan_subscriptions
from src.utils.logger import Logger
import os
import httpx

load_dotenv()

REFRESH_INTERVAL_MINUTES = int(os.getenv("REFRESH_INTERVAL_MINUTES_TOKENS", 15))

async def wait_for_webhook_endpoint():
    """
    Verifica che l'endpoint webhook Microsoft sia raggiungibile prima di iniziare i refresh.
    """
    webhook_url = os.getenv("MICROSOFT_WEBHOOK_URL", "https://listeners.corretto.pro/microsoft/webhook")
    max_attempts = 5
    delay_between_attempts = 3
    
    Logger.log_info("### MICROSOFT SUBSCRIPTIONS 🔍 Verifica webhook endpoint...")
    
    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{webhook_url}?validationToken=healthcheck")
                
                if response.status_code == 200 and response.text == "healthcheck":
                    Logger.log_info("### MICROSOFT SUBSCRIPTIONS ✅ Webhook endpoint raggiungibile e funzionante!")
                    return True
                    
        except Exception as e:
            if attempt == max_attempts - 1:  # Solo ultimo tentativo
                Logger.log_warning(f"### MICROSOFT SUBSCRIPTIONS ⚠️ Webhook endpoint non raggiungibile: {str(e)}")
        
        if attempt < max_attempts - 1:
            await asyncio.sleep(delay_between_attempts)
    
    Logger.log_error(f"### MICROSOFT SUBSCRIPTIONS ❌ Webhook endpoint non raggiungibile dopo {max_attempts} tentativi. Continuando comunque...")
    return False

async def main():
    # Aspetta che i listener siano pronti prima di iniziare i controlli
    initial_delay = int(os.getenv("INITIAL_DELAY_SECONDS", 30))
    Logger.log_info(f"### MICROSOFT SUBSCRIPTIONS ⏳ Attesa di {initial_delay} secondi per permettere ai listener di avviarsi...")
    await asyncio.sleep(initial_delay)
    
    # Verifica che l'endpoint webhook sia raggiungibile
    await wait_for_webhook_endpoint()
    
    # Esegui una pulizia iniziale delle subscription orfane se richiesto
    if os.getenv("CLEANUP_ORPHAN_SUBSCRIPTIONS", "").lower() == "true":
        Logger.log_info("### MICROSOFT SUBSCRIPTIONS 🧹 Pulizia iniziale subscription orfane abilitata...")
        await cleanup_all_orphan_subscriptions()
    
    while True:
        Logger.log_info("### MICROSOFT SUBSCRIPTIONS 🔁 Controllo subscription Microsoft in scadenza...")
        await refresh_expiring_subscriptions()
        Logger.log_info(f"### MICROSOFT SUBSCRIPTIONS 💤 Attesa di {REFRESH_INTERVAL_MINUTES} minuti prima del prossimo controllo...")
        await asyncio.sleep(REFRESH_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    asyncio.run(main())