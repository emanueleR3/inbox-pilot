from fastapi import APIRouter, Depends, Body, status
from src.core.dependecy import get_current_user
from src.modules.auth.src.controllers.user_controller import UserController

router = APIRouter(tags=["Autenticazione Supa"])
controller = UserController()

@router.get(
    "/get-user/{email}",
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
    "/create-account",
    status_code=status.HTTP_201_CREATED,
    summary="Crea un nuovo account utente",
    description="""
    Crea un nuovo utente con la sua sottoscrizione associata. Effettua anche il login.
    """,
    responses={
        201: {
            "description": "Account creato con successo",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Registrazione completata",
                        "result": {
                            "id": "id_12345",
                            "email": "user@example.com",
                            "subscriptions": [
                                {
                                    "subscription_id": "sub_id12345",
                                    "name": "Palestra Torino17",
                                    "vat_number": "IT123456789",
                                    "city": "Torino",
                                    "address": "Corso Francia 100",
                                    "active": "true",
                                    "current_period_end": "2025-12-31T23:59:59Z",
                                    "plan": "Premium",
                                    "is_configurated": "false", 
                                    "industry": "Fitness",
                                }
                            ],
                            "jwt": "jwt_token",
                            "sub_selected": 0
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
                            "value": {"detail": "Email e password e i dati della sottoscrizione sono richiesti"}
                        },
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
                "industry": "Tecnologia",
            }
        },
        description="Email e password per la registrazione del nuovo utente.",
    )
):
    result = controller.create_user_with_sub(payload)
    return {"message": "Registrazione completata", "result": result}

@router.post(
    "/add-new-user",
    status_code=status.HTTP_201_CREATED,
    summary="Crea un nuovo account non admin",
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
                            True
                        }
                    }
                }
            }
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "examples": {
                    "missing_fields": {
                        "value": {"detail": "Email e password e dettagli della subscription sono richiesti"}
                    },
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
def add_new_user(
    payload: dict = Body(
        ...,
        example={
            "email": "user@example.com", 
            "password": "strongpassword123",
            "subscription_id": "sub_id"
        },
        description="Email e password per la registrazione del nuovo utente.",
    ),
    #current_user=Depends(get_current_user)
):
    result = controller.add_new_user(payload)
    return {"message": "Registrazione completata", "result": result}

@router.post(
    "/create-new-subs",
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nuova subscriptione",
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
                                "id": "35e26201-6c9f-4933-806e-315cefe20b73",
                                "email": "dev1@example.com",
                                "subscriptions": [
                                    {
                                        "subscription_id": "b81fdc42-59f5-4d7c-bf60-95e02bfd06fc",
                                        "name": "Emanuele Srl",
                                        "vat_number": "1234567890",
                                        "city": "Lecce",
                                        "address": "Via Enrico Fermi",
                                        "active": True,
                                        "current_period_end": "2026-01-22T16:36:59.451000Z",
                                        "plan": "personal",
                                        "website": "https://keplero.ai",
                                        "industry": "Informatica",
                                        "is_configurated": True
                                    },
                                    {
                                        "subscription_id": "4abd29ef-8e47-4714-947e-6a472661433d",
                                        "name": "Acme Inc",
                                        "vat_number": "1\\234567890",
                                        "city": "Milan",
                                        "address": "Via Roma 1",
                                        "active": True,
                                        "current_period_end": "2026-03-16T21:45:03.050000Z",
                                        "plan": "trial",
                                        "website": None,
                                        "industry": None,
                                        "is_configurated": False
                                    }
                                ],
                                "jwt": "jwt_token",
                                "sub_selected": 1
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
                            "value": {"detail": "Email e password e dettagli della subscription sono richiesti"}
                        },
                    }
                }
            }
        },
        409: {
            "description": "Conflitto",
            "content": {
                "application/json": {
                    "example": {"detail": "Questa sottoscrizione esiste già"}
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
def create_new_sub(
    payload: dict = Body(
        ...,
        example={
            "user": {
                "id": "userid",
                "email": "user@example.com"
            },
            "jwt": "jwt_token",
            "subscription": {
                "name": "Palestra Torino123",
                "vat_number": "IT123456789",
                "city": "Torino",
                "address": "Corso Francia 100",
                "active": True,
                "current_period_end": "2025-12-31T23:59:59Z",
                "plan": "Premium",
                "industry": "Fitness"
            }
        },
        description="Crea e collega una nuova subscription a un account già esistente (user + jwt).",
    )
):
    result = controller.create_new_sub(payload)
    return {"message": "Registrazione completata", "result": result}

@router.get(
    "/get-users-subscription/{subscription_id}",
    status_code=200,
    summary="Recupera tutti gli utenti di una sottoscrizione",
    description="""
    Questa endpoint restituisce tutti gli utenti (`id`, `email`) 
    associati a una specifica sottoscrizione.

    🔹 Usa la relazione `users_has_subscriptions` nel database  
    🔹 Filtra gli utenti registrati in Supabase Auth
    """,
    responses={
        200: {"description": "Lista di utenti trovata con successo"},
        400: {"description": "ID sottoscrizione mancante o non valido"},
        404: {"description": "Nessun utente trovato per questa sottoscrizione"},
        500: {"description": "Errore interno del server"}
    }
)
def get_users_by_subscription(subscription_id: str):
    return controller.get_users_by_subscription(subscription_id)

@router.post(
    "/login",
    summary="Login utente",
    description="""
    Esegue il login di un utente fornendo email e password.
    
    - Richiede email e password validi
    - Verifica le credenziali contro Supabase Auth
    - Restituisce un token di sessione in caso di successo
    - Per ogni subscription ritorna anche i `subscription_services` associati nel campo `services`
    """,
    responses={
        200: {
            "description": "Login effettuato con successo",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Login effettuato",
                        "result": {
                            "id": "id_12345",
                            "email": "user@example.com",
                            "subscriptions": [
                                {
                                    "subscription_id": "sub_id12345",
                                    "name": "Name Srl",
                                    "vat_number": "0987654321",
                                    "city": "Lecce",
                                    "address": "Via Enrico Fermi, 8",
                                    "active": "true",
                                    "current_period_end": "2025-12-20T00:00:00Z",
                                    "plan": "personal",
                                    "website": "www.namesrl.com",
                                    "industry": "Tecnologia",
                                    "is_configurated": "true",
                                    "services": [
                                        {
                                            "service_id": "b6b3405a-e42f-42e3-9b29-0d5419481aba",
                                            "email": "user@example.com",
                                            "subscription_id": "sub_id12345",
                                            "email_provider": "google",
                                            "calendar_provider": "google",
                                            "config_completed": False,
                                            "activated": False,
                                            "draft": True,
                                            "name": "Nome Attività"
                                        }
                                    ]
                                }
                            ],
                            "jwt": "jwt_token",
                            "sub_selected": 0
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
                    }
                }
            }
        },
        401: {
            "description": "Autenticazione fallita",
            "content": {
                "application/json": {
                    "example": {"detail": "Credenziali non valide"}
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore interno nel servizio di autenticazione"}
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
    result = controller.login_user(payload)
    return {"message": "Login effettuato", "result": result}



@router.post(
    "/magic-link",
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
    "/reset-password",
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
    "/update-password",
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
    ),
    current_user=Depends(get_current_user)
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
    controller.logout()
    return {"message": "Logout effettutato"}

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
    controller.delete_account(user_id)
    return {"message": "Account cancellato"}

@router.get(
    "/get-subscription/{subscription_id}",
    summary="Recupera i dati di una sottoscrizione",
    description="Restituisce tutti i dettagli della sottoscrizione identificata dall'ID specificato.",
    responses={
        200: {
            "description": "Sottoscrizione trovata",
            "content": {
                "application/json": {
                    "example": {
                        "subscription_id": "d7a8dfe2-47af-4c98-a02c-2fcb49c4716c",
                        "name": "ACME S.r.l.",
                        "vat_number": "IT123456789",
                        "city": "Milano",
                        "address": "Via Roma 1",
                        "active": True,
                        "plan": "pro",
                        "current_period_end": "2025-12-01T12:00:00Z"
                    }
                }
            }
        },
        404: {"description": "Sottoscrizione non trovata"},
        500: {"description": "Errore interno del server"}
    }
)
async def get_subscription_by_id(subscription_id: str):
    return controller.get_subscription_by_id(subscription_id)
