from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
from src.core.logger import setup_logger
from src.modules.auth.src.utils.google_oauth_client import create_google_flow
from src.modules.auth.src.utils.microsoft_oauth_client import (
    create_microsoft_auth_url,
    exchange_code_for_tokens
)
from src.modules.google.src.controllers.gmail_watch_controller import create_watch_for_user
from src.modules.microsoft.src.controllers.graph_subscription_controller import (
    create_subscription_for_user
)
from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO
import os
import requests
import httpx
import json
import base64
import time

# Assicurati che la variabile sia impostata
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

logger = setup_logger()
subscription_service_dao = SubscriptionServiceDAO()


class OAuthLoginRequest(BaseModel):
    subscription_id: str
    services: str  # "all" o "calendar"
    email: Optional[str] = None  # Email opzionale per services="calendar"


async def oauth_login(provider_name: str, oauth_request: OAuthLoginRequest, request: Request):
    """
    Gestisce il login OAuth per Google o Microsoft con subscription_id dal body.
    """
    try:
        subscription_id = oauth_request.subscription_id
        services = oauth_request.services
        email = oauth_request.email
        logger.info(f"Starting OAuth login for provider: {provider_name}, subscription_id: {subscription_id}, services: {services}, email: {email}")
        
        if provider_name.lower() == "google":
            return await _google_login(subscription_id, services, email, request)
        elif provider_name.lower() == "microsoft":
            return await _microsoft_login(subscription_id, services, email, request)
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")
            
    except Exception as e:
        logger.error(f"Error in OAuth login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during OAuth login")


async def _google_login(subscription_id: str, services: str, email: str, request: Request):
    """
    Gestisce il login Google con subscription_id, services e email.
    """
    flow = create_google_flow(services)
    
    # Crea uno stato personalizzato che include subscription_id, services e email
    custom_state = {
        "subscription_id": subscription_id,
        "services": services,
        "email": email,  # Può essere None
        "timestamp": str(int(time.time()))
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(custom_state).encode()).decode()
    
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=encoded_state
    )

    logger.info(f"Returning Google OAuth URL: {authorization_url}")
    
    # CAMBIA QUESTO: Restituisci JSON invece di RedirectResponse
    return JSONResponse(content={
        "success": True,
        "url": authorization_url,
        "message": "Google OAuth URL generated successfully"
    })

async def _microsoft_login(subscription_id: str, services: str, email: str, request: Request):
    """
    Gestisce il login Microsoft con subscription_id, services e email.
    """
    # Crea uno stato personalizzato che include subscription_id, services e email (come Google)
    custom_state = {
        "subscription_id": subscription_id,
        "services": services,
        "email": email,  # Può essere None
        "timestamp": str(int(time.time()))
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(custom_state).encode()).decode()
    
    # Usa la funzione modificata che accetta lo state personalizzato
    authorization_url = create_microsoft_auth_url(encoded_state)
    
    logger.info(f"Returning Microsoft OAuth URL: {authorization_url}")
    
    # CAMBIA QUESTO: Restituisci JSON invece di RedirectResponse
    return JSONResponse(content={
        "success": True,
        "url": authorization_url,
        "message": "Microsoft OAuth URL generated successfully"
    })


async def google_callback(request: Request):
    """
    Gestisce il callback dopo il login Google.
    """
    try:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        
        # Prova a recuperare subscription_id, services e email dallo stato OAuth
        subscription_id = None
        services = None
        payload_email = None
        state = request.query_params.get("state")
        
        if state:
            try:
                decoded_state = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
                subscription_id = decoded_state.get("subscription_id")
                services = decoded_state.get("services")
                payload_email = decoded_state.get("email")  # Email dal payload
                logger.info(f"Retrieved from OAuth state - subscription_id: {subscription_id}, services: {services}, payload_email: {payload_email}")
            except Exception as e:
                logger.warning(f"Could not decode OAuth state: {e}")
        
        # Fallback ai query parameters e poi ai cookie
        if not subscription_id:
            subscription_id = request.query_params.get("subscription_id") or request.cookies.get("subscription_id")
        if not services:
            services = request.query_params.get("services") or request.cookies.get("services") or "all"  # default to "all"
        if not payload_email: # TODO possibile errore visto che None è corretto
            payload_email = request.query_params.get("email") or request.cookies.get("email")
        
        if not subscription_id:
            logger.error("Missing subscription_id from state, query params and cookies")
            raise HTTPException(status_code=400, detail="Missing subscription_id from login session")
        
        logger.info(f"Using subscription_id: {subscription_id}, services: {services}, payload_email: {payload_email}")
        
        flow = create_google_flow(services)
        
        # Costruisci l'URL di callback con lo scheme HTTPS per il reverse proxy
        callback_url = str(request.url)        
        if callback_url.startswith("http://") and "X-Forwarded-Proto" in request.headers:
            callback_url = callback_url.replace("http://", "https://", 1)
        
        logger.info(f"Processing Google callback with URL: {callback_url}")
        
        flow.fetch_token(authorization_response=callback_url)
        credentials = flow.credentials

        # Verifica che il token sia valido testando una chiamata API
        try:
            user_info_response = requests.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"}
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch user info: {e}")
            raise HTTPException(status_code=400, detail="Invalid Google token")

        email = user_info["email"]  # Email dall'account Google autenticato
        logger.info(f"Authenticated Google user: {email}")

        # Verifica che abbiamo tutti i dati necessari
        if not credentials.token:
            raise HTTPException(status_code=400, detail="Access token mancante")
        
        if not credentials.refresh_token:
            logger.warning("Refresh token mancante - potrebbe essere necessario revocare e riautorizzare")

        # Salva le credenziali nel database
        access_token = credentials.token
        refresh_token = credentials.refresh_token
        expiry = credentials.expiry

        # Determina quale email usare per il salvataggio nel database
        if services == "calendar":
            # Per calendar-only, usa l'email dal payload se fornita
            db_email = payload_email
        else:
            # Per "all" o se non c'è payload_email, usa l'email dell'account autenticato
            db_email = email

        logger.info(f"Saving credentials for {db_email} with subscription_id: {subscription_id}")

        # Crea la watch Gmail SOLO se services è "all"
        history_id = None
        if services == "all":
            try:
                logger.info(f"Creating Gmail watch for {email} (services: {services})")  # Usa sempre l'email autenticata per la watch
                response = create_watch_for_user(access_token=access_token, refresh_token=refresh_token, user_email=email)
                logger.info(f"Gmail watch response: {response}")
                
                history_id = response.get("historyId")
                if not history_id:
                    logger.warning(f"No historyId received from Gmail watch response for {email}")
                    
            except Exception as watch_error:
                logger.error(f"Failed to create Gmail watch for {email}: {watch_error}")
                logger.warning("Continuing authentication process despite watch creation failure")
        else:
            logger.info(f"Skipping Gmail watch creation for {email} (services: {services})")
        
        # Salva nel database usando il subscription_id dalla richiesta
        try:
            # Ora utilizziamo i parametri aggiornati del DAO
            if services == "calendar":
                logger.info(f"Saving Google credentials for calendar-only access (email: {db_email})")
                result = subscription_service_dao.save_google_credentials(
                    email=db_email,  # Usa l'email dal payload per calendar-only
                    subscription_id=subscription_id, 
                    access_token=access_token, 
                    refresh_token=refresh_token, 
                    expiry=expiry, 
                    history_id=history_id  # Sarà None per calendar-only
                )
            else:
                logger.info(f"Saving Google credentials for full access (email: {db_email})")
                result = subscription_service_dao.save_google_credentials(
                    email=db_email,  # Usa l'email dell'account autenticato per full access
                    subscription_id=subscription_id, 
                    access_token=access_token, 
                    refresh_token=refresh_token, 
                    expiry=expiry, 
                    history_id=history_id  # Conterrà il valore reale per full access
                )
            if result is False:
                logger.error("Errore nel salvataggio delle credenziali Google nel database")
                raise HTTPException(status_code=500, detail="Errore nel salvataggio delle credenziali Google")
            logger.info(f"Credentials saved successfully for {db_email}")
        except Exception as save_error:
            logger.error(f"Database error saving credentials: {save_error}")
            raise HTTPException(status_code=500, detail="Errore database nel salvataggio credenziali")

        token_data = {
            "email": db_email,  # Email usata nel database
            "authenticated_email": email,  # Email dell'account Google autenticato
            "subscription_id": subscription_id,
            "services": services,
            "provider": "google",
            "calendar_only": services == "calendar",
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expiry": str(credentials.expiry) if credentials.expiry else None
        }

        logger.info(f"Google authentication completed successfully for {email}, saved as {db_email}")
        
        # Restituisci HTML che chiude il popup e invia messaggio al parent
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Successful</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: #f5f5f5;
                }}
                .success {{
                    color: #28a745;
                    font-size: 18px;
                }}
            </style>
        </head>
        <body>
            <div class="success">
                <h2>✅ Login completato con successo!</h2>
                <p>Questa finestra si chiuderà automaticamente...</p>
            </div>
            <script>
                try {{
                    // Invia messaggio al parent window (la pagina principale)
                    if (window.opener) {{
                        window.opener.postMessage({{
                            success: true,
                            message: "Google account connesso con successo!",
                            user: {json.dumps(token_data)}
                        }}, "*");
                    }}
                    
                    // Chiudi la finestra popup dopo un breve delay
                    setTimeout(() => {{
                        window.close();
                    }}, 2000);
                }} catch (error) {{
                    console.error("Error sending message to parent:", error);
                    window.close();
                }}
            </script>
        </body>
        </html>
        """
        
        # Pulisci i cookie prima di restituire la risposta
        response = HTMLResponse(content=html_content)
        response.delete_cookie("oauth_state")
        response.delete_cookie("subscription_id")
        return response

    except HTTPException as e:
        # In caso di errore HTTPException
        logger.error(f"HTTP Exception in Google callback: {e.detail}")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Error</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: #f5f5f5;
                }}
                .error {{
                    color: #dc3545;
                    font-size: 18px;
                }}
            </style>
        </head>
        <body>
            <div class="error">
                <h2>❌ Errore durante il login</h2>
                <p>{e.detail}</p>
                <p>Questa finestra si chiuderà automaticamente...</p>
            </div>
            <script>
                try {{
                    if (window.opener) {{
                        window.opener.postMessage({{
                            success: false,
                            error: "{e.detail}"
                        }}, "*");
                    }}
                    
                    setTimeout(() => {{
                        window.close();
                    }}, 3000);
                }} catch (error) {{
                    console.error("Error sending message to parent:", error);
                    window.close();
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except Exception as e:
        # In caso di errore generico
        logger.error(f"Errore nel callback Google: {e}", exc_info=True)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Error</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: #f5f5f5;
                }}
                .error {{
                    color: #dc3545;
                    font-size: 18px;
                }}
            </style>
        </head>
        <body>
            <div class="error">
                <h2>❌ Errore durante l'autenticazione Google</h2>
                <p>Si è verificato un errore imprevisto. Riprova più tardi.</p>
                <p>Questa finestra si chiuderà automaticamente...</p>
            </div>
            <script>
                try {{
                    if (window.opener) {{
                        window.opener.postMessage({{
                            success: false,
                            error: "Errore autenticazione Google"
                        }}, "*");
                    }}
                    
                    setTimeout(() => {{
                        window.close();
                    }}, 3000);
                }} catch (error) {{
                    console.error("Error sending message to parent:", error);
                    window.close();
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)


async def microsoft_callback(request: Request):
    """
    Gestisce il callback dopo il login Microsoft.
    """
    try:
        # Prova a recuperare subscription_id, services e email dallo stato OAuth (come Google)
        subscription_id = None
        services = None
        payload_email = None
        state = request.query_params.get("state")
        
        if state:
            try:
                decoded_state = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
                subscription_id = decoded_state.get("subscription_id")
                services = decoded_state.get("services")
                payload_email = decoded_state.get("email")  # Email dal payload
                logger.info(f"Retrieved from Microsoft OAuth state - subscription_id: {subscription_id}, services: {services}, payload_email: {payload_email}")
            except Exception as e:
                logger.warning(f"Could not decode Microsoft OAuth state: {e}")
        
        # Fallback ai query parameters e poi ai cookie (per compatibilità)
        if not subscription_id:
            subscription_id = request.query_params.get("subscription_id") or request.cookies.get("subscription_id")
        if not services:
            services = request.query_params.get("services") or request.cookies.get("services") or "all"  # default to "all"
        # TODO possibile errore visto che None è corretto
        if not payload_email:
            payload_email = request.query_params.get("email") or request.cookies.get("email")
        
        if not subscription_id:
            logger.error("Missing subscription_id from state, query params and cookies")
            raise HTTPException(status_code=400, detail="Missing subscription_id from login session")
        
        logger.info(f"Microsoft callback URL: {request.url}")
        logger.info(f"Using subscription_id: {subscription_id}, services: {services}, payload_email: {payload_email}")
        
        # Controlla se c'è un errore da Microsoft
        error = request.query_params.get("error")
        error_description = request.query_params.get("error_description")
        
        if error:
            logger.error(f"Microsoft OAuth error: {error}")
            logger.error(f"Error description: {error_description}")
            raise HTTPException(status_code=400, detail=f"Microsoft OAuth error: {error} - {error_description}")
        
        code = request.query_params.get("code")
        if not code:
            logger.error("No authorization code in callback")
            raise HTTPException(status_code=400, detail="Missing authorization code")

        logger.info(f"Authorization code received: {code[:20]}...")

        # Scambio del codice con i token usando gli scope appropriati
        tokens = await exchange_code_for_tokens(code, services)
        access_token = tokens.get("access_token")

        logger.info("Microsoft tokens retrieved successfully")

        # Recupera informazioni sull'utente
        async with httpx.AsyncClient() as client:
            user_info_response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()

        email = user_info.get("userPrincipalName")  # Email dall'account Microsoft autenticato
        user_id = user_info.get("id")
        refresh_token = tokens.get("refresh_token")
        expiry = tokens.get("expires_in")

        logger.info(f"Authenticated Microsoft user: {email}")

        # Determina quale email usare per il salvataggio nel database
        if services == "calendar":
            # Per calendar-only, usa l'email dal payload se fornita
            db_email = payload_email
        else:
            # Per "all" o se non c'è payload_email, usa l'email dell'account autenticato
            db_email = email

        logger.info(f"Saving Microsoft credentials for {db_email} with subscription_id: {subscription_id}") 

        # Crea la subscription per ricevere notifiche email SOLO se services è "all"
        subscription = None
        if services == "all":
            try:
                logger.info(f"Creating Microsoft Graph subscription for {email} (services: {services})")
                subscription = await create_subscription_for_user(access_token, user_id)
                
                # Log dettagliato delle subscription create
                if isinstance(subscription, list):
                    logger.info(f"Microsoft subscriptions created for {email}: {len(subscription)} subscription(s)")
                    for sub in subscription:
                        folder_type = sub.get("folder_type", "unknown")
                        sub_id = sub.get("id", "unknown")
                        logger.info(f"  - {folder_type.upper()} subscription: {sub_id}")
                else:
                    logger.info(f"Microsoft subscription created for {email}: {subscription}")
                    
            except Exception as sub_error:
                logger.error(f"Failed to create Microsoft subscription for {email}: {sub_error}")
                logger.warning("Continuing authentication process despite subscription creation failure")
        else:
            logger.info(f"Skipping Microsoft Graph subscription creation for {email} (services: {services})")

        # Salva nel database usando il subscription_id dalla richiesta
        # Ora utilizziamo i parametri aggiornati del DAO per gestire entrambe le subscription
        if services == "calendar":
            logger.info(f"Saving Microsoft credentials for calendar-only access (email: {email})")
            result = subscription_service_dao.save_microsoft_credentials(
                email=db_email, 
                subscription_id=subscription_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expiry=expiry,
                microsoft_subscription_id_inbound=None,  # Nessuna subscription per calendar-only
                microsoft_subscription_id_outbound=None,  # Nessuna subscription per calendar-only
                microsoft_expiration_datetime_inbound=None,
                microsoft_expiration_datetime_outbound=None
            )
        else:
            logger.info(f"Saving Microsoft credentials for full access (email: {email})")
            # Per full access, subscription è una lista con inbound e outbound
            inbound_sub = None
            outbound_sub = None
            
            if isinstance(subscription, list):
                for sub in subscription:
                    folder_type = sub.get("folder_type")
                    if folder_type == "inbox":
                        inbound_sub = sub
                    elif folder_type == "sent":
                        outbound_sub = sub
            
            result = subscription_service_dao.save_microsoft_credentials(
                email=db_email, 
                subscription_id=subscription_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expiry=expiry,
                microsoft_subscription_id_inbound=inbound_sub.get("id") if inbound_sub else None,
                microsoft_subscription_id_outbound=outbound_sub.get("id") if outbound_sub else None,
                microsoft_expiration_datetime_inbound=inbound_sub.get("expirationDateTime") if inbound_sub else None,
                microsoft_expiration_datetime_outbound=outbound_sub.get("expirationDateTime") if outbound_sub else None
            )

        if result is False:
            logger.error("Errore nel salvataggio delle credenziali Microsoft")
            raise HTTPException(status_code=500, detail="Errore nel salvataggio delle credenziali Microsoft")

        token_data = {
            "email": email,
            "subscription_id": subscription_id,
            "services": services,
            "provider": "microsoft",
            "calendar_only": services == "calendar",
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expiry": tokens.get("expires_in"),
        }

        logger.info(f"Microsoft authentication completed successfully for {email}")
        
        # Restituisci HTML che chiude il popup e invia messaggio al parent
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Successful</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: #f5f5f5;
                }}
                .success {{
                    color: #28a745;
                    font-size: 18px;
                }}
            </style>
        </head>
        <body>
            <div class="success">
                <h2>✅ Login completato con successo!</h2>
                <p>Questa finestra si chiuderà automaticamente...</p>
            </div>
            <script>
                try {{
                    // Invia messaggio al parent window (la pagina principale)
                    if (window.opener) {{
                        window.opener.postMessage({{
                            success: true,
                            message: "Microsoft account connesso con successo!",
                            user: {json.dumps(token_data)},
                            subscription: {json.dumps(subscription)}
                        }}, "*");
                    }}
                    
                    // Chiudi la finestra popup dopo un breve delay
                    setTimeout(() => {{
                        window.close();
                    }}, 2000);
                }} catch (error) {{
                    console.error("Error sending message to parent:", error);
                    window.close();
                }}
            </script>
        </body>
        </html>
        """
        
        # Pulisci i cookie prima di restituire la risposta
        response = HTMLResponse(content=html_content)
        response.delete_cookie("subscription_id")
        return response

    except HTTPException as e:
        # In caso di errore HTTPException
        logger.error(f"HTTP Exception in Microsoft callback: {e.detail}")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Error</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: #f5f5f5;
                }}
                .error {{
                    color: #dc3545;
                    font-size: 18px;
                }}
            </style>
        </head>
        <body>
            <div class="error">
                <h2>❌ Errore durante il login</h2>
                <p>{e.detail}</p>
                <p>Questa finestra si chiuderà automaticamente...</p>
            </div>
            <script>
                try {{
                    if (window.opener) {{
                        window.opener.postMessage({{
                            success: false,
                            error: "{e.detail}"
                        }}, "*");
                    }}
                    
                    setTimeout(() => {{
                        window.close();
                    }}, 3000);
                }} catch (error) {{
                    console.error("Error sending message to parent:", error);
                    window.close();
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except Exception as e:
        # In caso di errore generico
        logger.error(f"Errore nel callback Microsoft: {e}")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Error</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: #f5f5f5;
                }}
                .error {{
                    color: #dc3545;
                    font-size: 18px;
                }}
            </style>
        </head>
        <body>
            <div class="error">
                <h2>❌ Errore durante l'autenticazione Microsoft</h2>
                <p>Si è verificato un errore imprevisto. Riprova più tardi.</p>
                <p>Questa finestra si chiuderà automaticamente...</p>
            </div>
            <script>
                try {{
                    if (window.opener) {{
                        window.opener.postMessage({{
                            success: false,
                            error: "Errore autenticazione Microsoft"
                        }}, "*");
                    }}
                    
                    setTimeout(() => {{
                        window.close();
                    }}, 3000);
                }} catch (error) {{
                    console.error("Error sending message to parent:", error);
                    window.close();
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
