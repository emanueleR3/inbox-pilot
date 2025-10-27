# refreshers/microsoft_subscription_refresher/src/subscription_refresher.py
import httpx
from src.utils.graph_client import renew_subscription
from src.db_client import get_subscriptions_expiring_soon, update_subscription_expiration
from src.utils.logger import Logger

async def delete_orphan_subscription(access_token: str, subscription_id: str):
    """
    Elimina una subscription orfana da Microsoft Graph.
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.delete(f"https://graph.microsoft.com/v1.0/subscriptions/{subscription_id}", headers=headers)
            
            if resp.status_code in [200, 204, 404]:  # 404 = già cancellata
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION 🗑️ Subscription orfana eliminata con successo: {subscription_id}")
                return True
            else:
                Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore nell'eliminazione subscription orfana {subscription_id}: {resp.status_code}")
                return False
                
    except Exception as e:
        Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore nell'eliminazione subscription orfana {subscription_id}: {str(e)}")
        return False

async def list_all_microsoft_subscriptions(access_token: str):
    """
    Lista tutte le subscription Microsoft Graph per questo token.
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://graph.microsoft.com/v1.0/subscriptions", headers=headers)
            
            if resp.status_code == 200:
                data = resp.json()
                subscriptions = data.get("value", [])
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION 📋 Trovate {len(subscriptions)} subscription totali per questo token")
                
                for sub in subscriptions:
                    Logger.log_info(f"   - ID: {sub.get('id')}, Resource: {sub.get('resource')}, Expiry: {sub.get('expirationDateTime')}")
                
                return subscriptions
            else:
                Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore nel recupero subscription: {resp.status_code}")
                return []
                
    except Exception as e:
        Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore nel recupero subscription: {str(e)}")
        return []

async def cleanup_all_orphan_subscriptions():
    """
    Pulisce tutte le subscription orfane per tutti gli utenti.
    """
    Logger.log_info("### MICROSOFT SUBSCRIPTION 🧹 Inizio pulizia globale subscription orfane...")
    
    # Ottieni tutte le subscription dal database
    expiring = await get_subscriptions_expiring_soon(threshold_minutes=60*24*30)  # Prendi tutte quelle che scadono nei prossimi 30 giorni
    
    for sub in expiring:
        try:
            Logger.log_info(f"### MICROSOFT SUBSCRIPTION 🔍 Controllo subscription orfane per {sub.get('email', 'unknown')}")
            
            # Lista tutte le subscription per questo token
            all_subs = await list_all_microsoft_subscriptions(sub["access_token"])
            
            # Filtra le subscription che non sono nel nostro database
            our_subscription_id = sub['subscription_id']
            orphan_subscriptions = [s for s in all_subs if s.get('id') != our_subscription_id and s.get('resource', '').startswith('/users/')]
            
            if orphan_subscriptions:
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION 🗑️ Trovate {len(orphan_subscriptions)} subscription orfane per {sub.get('email', 'unknown')}")
                
                # Elimina le subscription orfane
                deleted_count = 0
                for orphan in orphan_subscriptions:
                    orphan_id = orphan.get('id')
                    Logger.log_info(f"### MICROSOFT SUBSCRIPTION 🗑️ Eliminazione subscription orfana: {orphan_id}")
                    success = await delete_orphan_subscription(sub["access_token"], orphan_id)
                    if success:
                        deleted_count += 1
                
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ Eliminate {deleted_count}/{len(orphan_subscriptions)} subscription orfane per {sub.get('email', 'unknown')}")
            else:
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ Nessuna subscription orfana trovata per {sub.get('email', 'unknown')}")
                
        except Exception as e:
            Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore nella pulizia subscription orfane per {sub.get('email', 'unknown')}: {str(e)}")
    
    Logger.log_info("### MICROSOFT SUBSCRIPTION 🧹 Pulizia globale subscription orfane completata")

async def refresh_expiring_subscriptions():
    expiring = await get_subscriptions_expiring_soon(threshold_minutes=15)

    for sub in expiring:
        try:
            Logger.log_info(f"### MICROSOFT SUBSCRIPTION 🔄 Tentativo di rinnovo per subscription: {sub['subscription_id']} (email: {sub.get('email', 'unknown')})")
            
            # Prima di rinnovare, lista tutte le subscription per questo token
            all_subs = await list_all_microsoft_subscriptions(sub["access_token"])
            
            # Filtra le subscription che non sono nel nostro database
            our_subscription_id = sub['subscription_id']
            orphan_subscriptions = [s for s in all_subs if s.get('id') != our_subscription_id and s.get('resource', '').startswith('/users/')]
            
            if orphan_subscriptions:
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION 🧹 Trovate {len(orphan_subscriptions)} subscription orfane per {sub.get('email', 'unknown')}")
                
                # Elimina le subscription orfane
                deleted_count = 0
                for orphan in orphan_subscriptions:
                    orphan_id = orphan.get('id')
                    Logger.log_info(f"### MICROSOFT SUBSCRIPTION 🗑️ Eliminazione subscription orfana: {orphan_id}")
                    success = await delete_orphan_subscription(sub["access_token"], orphan_id)
                    if success:
                        deleted_count += 1
                
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ Eliminate {deleted_count}/{len(orphan_subscriptions)} subscription orfane per {sub.get('email', 'unknown')}")
            else:
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ Nessuna subscription orfana trovata per {sub.get('email', 'unknown')}")
            
            # Ora rinnova la subscription corretta
            renewed = await renew_subscription(sub["access_token"], sub["subscription_id"])
            new_expiration = renewed["expirationDateTime"]

            await update_subscription_expiration(sub["subscription_id"], new_expiration)
            Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ Subscription rinnovata con successo: {sub['subscription_id']}")

        except Exception as e:
            Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore nel rinnovo della subscription {sub['subscription_id']} (email: {sub.get('email', 'unknown')}): {str(e)}")
            # Log più dettagliato per capire il tipo di errore
            if "ValidationError" in str(e):
                Logger.log_error(f"### MICROSOFT SUBSCRIPTION 🔍 Errore di validazione webhook - Microsoft non riesce a validare l'endpoint")
            elif "400" in str(e):
                Logger.log_error(f"### MICROSOFT SUBSCRIPTION 🔍 Errore 400 - Bad Request dal Graph API")
            elif "401" in str(e):
                Logger.log_error(f"### MICROSOFT SUBSCRIPTION 🔍 Errore 401 - Token di accesso scaduto o non valido")