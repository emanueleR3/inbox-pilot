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
    Ora gestisce sia subscription inbound che outbound.
    """
    Logger.log_info("### MICROSOFT SUBSCRIPTION 🧹 Inizio pulizia globale subscription orfane (INBOUND 📥 + OUTBOUND 📤)...")
    
    # Ottieni tutte le subscription dal database (sia inbound che outbound)
    expiring = await get_subscriptions_expiring_soon(threshold_minutes=30)  # Prendi tutte quelle che scadono nei prossimi 30 minuti
    
    # Raggruppa per utente (stesso access token)
    users_processed = set()
    
    for sub in expiring:
        try:
            email = sub.get('email', 'unknown')
            access_token = sub["access_token"]
            
            # Evita di processare lo stesso utente più volte
            if email in users_processed:
                continue
            users_processed.add(email)
            
            Logger.log_info(f"### MICROSOFT SUBSCRIPTION 🔍 Controllo subscription orfane per {email} (INBOUND 📥 + OUTBOUND 📤)")
            
            # Lista tutte le subscription per questo token
            all_subs = await list_all_microsoft_subscriptions(access_token)
            
            # Ottieni tutte le subscription di questo utente dal database
            our_subscription_ids = []
            inbound_count = 0
            outbound_count = 0
            
            # Raccogli tutte le subscription inbound e outbound per questo utente
            user_subs = [s for s in expiring if s.get('email') == email]
            for user_sub in user_subs:
                our_subscription_ids.append(user_sub['subscription_id'])
                if user_sub.get('subscription_type') == 'inbound':
                    inbound_count += 1
                elif user_sub.get('subscription_type') == 'outbound':
                    outbound_count += 1
            
            Logger.log_info(f"   🎯 Subscription registrate: {inbound_count} INBOUND 📥 + {outbound_count} OUTBOUND 📤")
            
            # Filtra le subscription che non sono nel nostro database
            orphan_subscriptions = [s for s in all_subs if s.get('id') not in our_subscription_ids and s.get('resource', '').startswith('/users/')]
            
            if orphan_subscriptions:
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION 🗑️ Trovate {len(orphan_subscriptions)} subscription orfane per {email}")
                
                # Elimina le subscription orfane
                deleted_count = 0
                for orphan in orphan_subscriptions:
                    orphan_id = orphan.get('id')
                    success = await delete_orphan_subscription(access_token, orphan_id)
                    if success:
                        deleted_count += 1
                
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ Eliminate {deleted_count}/{len(orphan_subscriptions)} subscription orfane per {email}")
            else:
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ Nessuna subscription orfana trovata per {email}")
                
        except Exception as e:
            Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ Errore nella pulizia subscription orfane per {sub.get('email', 'unknown')}: {str(e)}")
    
    Logger.log_info("### MICROSOFT SUBSCRIPTION 🧹 Pulizia globale subscription orfane completata (INBOUND 📥 + OUTBOUND 📤)")

async def refresh_expiring_subscriptions():
    """
    Rinnova le subscription Microsoft in scadenza, gestendo sia inbound che outbound.
    """
    expiring = await get_subscriptions_expiring_soon(threshold_minutes=15)

    for sub in expiring:
        try:
            subscription_type = sub.get("subscription_type", "inbound")
            subscription_id = sub["subscription_id"]
            email = sub.get("email", "unknown")
            
            # Emoji diversi per subscription inbound e outbound
            type_emoji = "📥" if subscription_type == "inbound" else "📤"
            folder_type = "Inbox" if subscription_type == "inbound" else "SentItems"
            
            Logger.log_info(f"### MICROSOFT SUBSCRIPTION 🔄 {type_emoji} Tentativo di rinnovo subscription {subscription_type.upper()} ({folder_type}): {subscription_id} (email: {email})")
            
            # Prima di rinnovare, lista tutte le subscription per questo token per trovare orfane
            all_subs = await list_all_microsoft_subscriptions(sub["access_token"])
            
            # Filtra le subscription che non sono nel nostro database
            our_subscription_ids = [subscription_id]  # Solo la subscription corrente
            orphan_subscriptions = [s for s in all_subs if s.get('id') not in our_subscription_ids and s.get('resource', '').startswith('/users/')]
            
            if orphan_subscriptions:
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION 🧹 Trovate {len(orphan_subscriptions)} subscription orfane per {email}")
                
                # Elimina le subscription orfane
                deleted_count = 0
                for orphan in orphan_subscriptions:
                    orphan_id = orphan.get('id')
                    success = await delete_orphan_subscription(sub["access_token"], orphan_id)
                    if success:
                        deleted_count += 1
                
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ Eliminate {deleted_count}/{len(orphan_subscriptions)} subscription orfane per {email}")
            else:
                Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ Nessuna subscription orfana trovata per {email}")
            
            # Rinnova la subscription corrente
            renewed = await renew_subscription(sub["access_token"], subscription_id)
            new_expiration = renewed["expirationDateTime"]

            # Aggiorna la scadenza nel database specificando il tipo di subscription
            await update_subscription_expiration(subscription_id, new_expiration, subscription_type)
            
            # Log dettagliato del successo con emoji specifici
            type_emoji = "📥" if subscription_type == "inbound" else "📤"
            folder_type = "Inbox" if subscription_type == "inbound" else "SentItems"
            Logger.log_info(f"### MICROSOFT SUBSCRIPTION ✅ {type_emoji} Subscription {subscription_type.upper()} ({folder_type}) rinnovata con successo!")
            Logger.log_info(f"   📧 Email: {email}")
            Logger.log_info(f"   🆔 Subscription ID: {subscription_id}")
            Logger.log_info(f"   📅 Nuova scadenza: {new_expiration}")

        except Exception as e:
            subscription_type = sub.get("subscription_type", "unknown")
            subscription_id = sub.get("subscription_id", "unknown")
            email = sub.get("email", "unknown")
            
            # Emoji diversi per subscription inbound e outbound negli errori
            type_emoji = "📥" if subscription_type == "inbound" else "📤" if subscription_type == "outbound" else "❓"
            folder_type = "Inbox" if subscription_type == "inbound" else "SentItems" if subscription_type == "outbound" else "Unknown"
            
            Logger.log_error(f"### MICROSOFT SUBSCRIPTION ❌ {type_emoji} Errore nel rinnovo subscription {subscription_type.upper()} ({folder_type})")
            Logger.log_error(f"   📧 Email: {email}")
            Logger.log_error(f"   🆔 Subscription ID: {subscription_id}")
            Logger.log_error(f"   🚨 Errore: {str(e)}")
            
            # Log più dettagliato per capire il tipo di errore
            if "ValidationError" in str(e):
                Logger.log_error(f"### MICROSOFT SUBSCRIPTION 🔍 {type_emoji} Errore di validazione webhook - Microsoft non riesce a validare l'endpoint per {folder_type}")
            elif "400" in str(e):
                Logger.log_error(f"### MICROSOFT SUBSCRIPTION 🔍 {type_emoji} Errore 400 - Bad Request dal Graph API per {folder_type}")
            elif "401" in str(e):
                Logger.log_error(f"### MICROSOFT SUBSCRIPTION 🔍 {type_emoji} Errore 401 - Token di accesso scaduto o non valido per {folder_type}")