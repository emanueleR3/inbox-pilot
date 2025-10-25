from fastapi import APIRouter, Depends, Body, HTTPException, status
from src.core.dependecy import get_current_user
from src.modules.auth.src.controllers.user_controller import UserController

router = APIRouter()
controller = UserController()

from fastapi import APIRouter, Body, Depends
from src.core.dependecy import get_current_user
from src.modules.auth.src.controllers.user_controller import UserController

router = APIRouter(tags=["Autenticazione Supa"])
controller = UserController()

@router.get(
    "/getUser/{email}",
    summary="Recupera un utente tramite email",
    description="Restituisce i dati dell’utente corrispondente all’indirizzo email fornito.",
    responses={
        200: {
            "description": "Utente trovato",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "abc123",
                        "email": "user@example.com",
                        "name": "Mario Rossi",
                    }
                }
            },
        },
        404: {"description": "Utente non trovato"},
    },
)
def get_user_by_email(email: str):
    return controller.get_user_by_email(email)

@router.post(
    "/createAccount",
    status_code=status.HTTP_201_CREATED,
    summary="Crea un nuovo account utente",
    description="""
    Crea un nuovo utente con la sua sottoscrizione associata.
    """,
    responses={
        201: {
            "description": "Account creato con successo",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Registrazione completata",
                        "result": {
                            "user_id": "abc123",
                            "email": "user@example.com",
                            "subscription": {
                                "subscription_id": "sub_xyz789",
                                "name": "TechVision Srl",
                                "plan": "premium",
                                "active": True
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_fields": {
                            "value": {"detail": "Email e password sono richiesti"}
                        },
                        "missing_subscription": {
                            "value": {"detail": "I dati della sottoscrizione sono richiesti"}
                        },
                        "weak_password": {
                            "value": {"detail": "Password troppo debole. Usa almeno 6 caratteri"}
                        }
                    }
                }
            }
        },
        409: {
            "description": "Conflitto",
            "content": {
                "application/json": {
                    "example": {"detail": "Un utente con questa email esiste già"}
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore durante la creazione dell'account"}
                }
            }
        }
    }
)
def create_user_with_sub(
    payload: dict = Body(
        ...,
        example={
            "email": "user@example.com", 
            "password": "strongpassword123",
            "subscription": {
                "name": "TechVision Srl",
                "vat_number": "IT12345678901",
                "city": "Milano",
                "address": "Via Roma 42",
                "active": True,
                "current_period_end": "2025-12-31T23:59:59Z",
                "plan": "premium",
            }
        },
        description="Email e password per la registrazione del nuovo utente.",
    )
):
    result = controller.create_user_with_sub(payload)
    return {"message": "Registrazione completata", "result": result}

@router.post(
    "/login",
    summary="Login utente",
    description="""
    Esegue il login di un utente fornendo email e password.
    
    - Richiede email e password validi
    - Verifica le credenziali contro Supabase Auth
    - Restituisce un token di sessione in caso di successo
    """,
    responses={
        200: {
            "description": "Login effettuato con successo",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Login effettuato",
                        "session": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh_token": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                            "expires_in": 3600,
                            "token_type": "bearer"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_fields": {
                            "value": {"detail": "Email e password sono richiesti"}
                        },
                        "unverified": {
                            "value": {"detail": "Email non verificata. Controlla la tua casella email"}
                        }
                    }
                }
            }
        },
        401: {
            "description": "Autenticazione fallita",
            "content": {
                "application/json": {
                    "example": {"detail": "Email o password non corretti"}
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore durante l'autenticazione"}
                }
            }
        }
    }
)
def login_user(
    payload: dict = Body(
        ...,
        example={"email": "user@example.com", "password": "strongpassword123"},
        description="Credenziali per accedere al proprio account.",
    )
):
    session = controller.login_user(payload)
    return {"message": "Login effettuato", "session": session}

@router.post(
    "/magicLink",
    summary="Invia un link magico per l'accesso",
    description="Invia via email un link magico per effettuare il login senza password.",
    responses={
        200: {
            "description": "Link magico inviato con successo",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Email con link di accesso inviata a user@example.com"
                    }
                }
            },
        },
        400: {"description": "Email non valida o non registrata"},
    },
)
def magic_link_login(
    payload: dict = Body(
        ...,
        example={"email": "user@example.com"},
        description="Email dell'utente a cui inviare il link magico di accesso.",
    )
):
    return controller.send_magic_link(payload)

@router.post(
    "/resetPassword",
    summary="Richiedi il reset della password",
    description="Invia un'email con le istruzioni per resettare la password.",
    responses={
        200: {
            "description": "Email di reset inviata con successo",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Email di reset inviata a user@example.com"
                    }
                }
            },
        },
        400: {"description": "Email non valida o non registrata"},
    },
)
def reset_password(
    payload: dict = Body(
        ...,
        example={"email": "user@example.com"},
        description="Email dell'utente che richiede il reset della password.",
    )
):
    return controller.reset_password(payload)

@router.post(
    "/updatePassword",
    summary="Aggiorna la password dell'utente",
    description="Permette di aggiornare la password fornendo quella vecchia e la nuova.",
    responses={
        200: {
            "description": "Password aggiornata con successo",
            "content": {
                "application/json": {
                    "example": {"message": "Password aggiornata correttamente"}
                }
            },
        },
        400: {"description": "Password non valida o richiesta incompleta"},
        401: {"description": "Credenziali non valide"},
    },
)
def update_password(
    payload: dict = Body(
        ...,
        example={
            "old_password": "vecchiapassword",
            "new_password": "nuovapasswordSicura123",
        },
        description="Vecchia e nuova password dell'utente.",
    )
):
    return controller.update_password(payload)

@router.post(
    "/logout",
    summary="Logout utente",
    description="Termina la sessione dell’utente attualmente autenticato.",
    responses={
        200: {
            "description": "Logout effettuato con successo",
            "content": {
                "application/json": {
                    "example": {"message": "Logout effettuato correttamente"}
                }
            },
        },
        401: {"description": "Utente non autenticato"},
    },
)
def logout(current_user=Depends(get_current_user)):
    return controller.logout()

@router.delete(
    "/delete/{user_id}",
    summary="Elimina un account utente",
    description="Elimina definitivamente l’account specificato dall’ID utente.",
    responses={
        200: {
            "description": "Account eliminato con successo",
            "content": {
                "application/json": {
                    "example": {"message": "Account eliminato correttamente"}
                }
            },
        },
        403: {"description": "Non autorizzato a eliminare questo account"},
        404: {"description": "Utente non trovato"},
    },
)
def delete_user(user_id: str, current_user=Depends(get_current_user)):
    return controller.delete_account(user_id)
