from fastapi import APIRouter, Body, status
from typing import Dict, Any
from src.modules.mailbox.src.controllers.mailbox_controller import MailboxController

router = APIRouter(
    tags=["Mailbox"]
)

controller = MailboxController()


@router.post(
    "/threads",
    status_code=status.HTTP_200_OK,
    summary="Recupera thread di conversazioni email",
    description="""
    Recupera i thread di conversazioni email dalla casella di posta.
    
    Supporta tre provider con un'interfaccia unificata:
    - **Google Gmail** (API Gmail)
    - **Microsoft Outlook** (Microsoft Graph API)
    - **IMAP** (Qualsiasi server IMAP)
    
    ## Provider supportati
    
    ### Google (`provider: "google"`)
    Utilizza le API Gmail per recuperare i thread.
    - Richiede un token OAuth valido
    - Supporta query di ricerca avanzate Gmail
    - I draft vengono automaticamente associati ai rispettivi thread
    
    ### Microsoft (`provider: "microsoft"`)
    Utilizza Microsoft Graph API per recuperare i messaggi.
    - Richiede un token OAuth valido
    - I messaggi vengono raggruppati per `conversationId`
    - Supporta la selezione della cartella
    
    ### IMAP (`provider: "imap"`)
    Connessione diretta al server IMAP.
    - Richiede credenziali IMAP (server, porta, email, password)
    - I messaggi vengono raggruppati per subject (threading semplificato)
    - I draft vengono cercati nelle cartelle: Drafts, [Gmail]/Drafts, INBOX.Drafts, Draft
    
    ## Inclusione Draft
    
    Il parametro `include_drafts` (default: `true`) controlla se includere le bozze:
    - **Gmail**: Recupera i draft e li associa ai thread esistenti
    - **Microsoft**: Recupera i messaggi dalla cartella "drafts"
    - **IMAP**: Cerca nella cartella Draft/Drafts del server
    
    ## Struttura Response
    
    Ogni thread contiene:
    - `id`: Identificativo univoco del thread
    - `subject`: Oggetto della conversazione
    - `snippet`: Anteprima del contenuto
    - `messages`: Lista completa dei messaggi (inclusi draft)
    - `message_count`: Numero totale di messaggi
    - `has_drafts`: Indica se ci sono bozze nel thread
    - `has_attachments`: Indica se ci sono allegati
    - `participants`: Lista di partecipanti alla conversazione
    - `last_message_date`: Data dell'ultimo messaggio
    - `is_unread`: Indica se ci sono messaggi non letti
    """,
    responses={
        200: {
            "description": "Lista di thread recuperati con successo",
            "content": {
                "application/json": {
                    "examples": {
                        "gmail_thread": {
                            "summary": "Thread Gmail con draft",
                            "value": [
                                {
                                    "id": "18d1234abcd5678",
                                    "subject": "Richiesta informazioni progetto",
                                    "snippet": "Grazie per la risposta, confermo la disponibilità...",
                                    "messages": [
                                        {
                                            "id": "msg_001",
                                            "subject": "Richiesta informazioni progetto",
                                            "snippet": "Buongiorno, vorrei richiedere...",
                                            "body_text": "Buongiorno,\n\nVorrei richiedere informazioni sul progetto X...",
                                            "body_html": None,
                                            "from_address": {
                                                "email": "cliente@example.com",
                                                "name": "Mario Rossi"
                                            },
                                            "to_addresses": [
                                                {"email": "info@azienda.com", "name": "Info Azienda"}
                                            ],
                                            "cc_addresses": [],
                                            "bcc_addresses": [],
                                            "date": "2025-01-02T10:30:00+00:00",
                                            "is_read": True,
                                            "is_draft": False,
                                            "attachments": [],
                                            "labels": ["INBOX", "IMPORTANT"]
                                        },
                                        {
                                            "id": "msg_002",
                                            "subject": "Re: Richiesta informazioni progetto",
                                            "snippet": "Grazie per la risposta...",
                                            "body_text": "Grazie per la risposta, confermo la disponibilità per un incontro.",
                                            "body_html": None,
                                            "from_address": {
                                                "email": "info@azienda.com",
                                                "name": "Info Azienda"
                                            },
                                            "to_addresses": [
                                                {"email": "cliente@example.com", "name": "Mario Rossi"}
                                            ],
                                            "cc_addresses": [],
                                            "bcc_addresses": [],
                                            "date": "2025-01-02T14:15:00+00:00",
                                            "is_read": True,
                                            "is_draft": False,
                                            "attachments": [
                                                {"filename": "proposta.pdf", "mime_type": "application/pdf", "size": 245678}
                                            ],
                                            "labels": ["SENT"]
                                        },
                                        {
                                            "id": "draft_001",
                                            "subject": "Re: Richiesta informazioni progetto",
                                            "snippet": "Perfetto, propongo...",
                                            "body_text": "Perfetto, propongo il seguente calendario...",
                                            "body_html": None,
                                            "from_address": {
                                                "email": "info@azienda.com",
                                                "name": "Info Azienda"
                                            },
                                            "to_addresses": [
                                                {"email": "cliente@example.com", "name": "Mario Rossi"}
                                            ],
                                            "cc_addresses": [],
                                            "bcc_addresses": [],
                                            "date": "2025-01-02T16:00:00+00:00",
                                            "is_read": True,
                                            "is_draft": True,
                                            "attachments": [],
                                            "labels": ["DRAFT"]
                                        }
                                    ],
                                    "message_count": 3,
                                    "has_drafts": True,
                                    "has_attachments": True,
                                    "participants": [
                                        {"email": "cliente@example.com", "name": "Mario Rossi"},
                                        {"email": "info@azienda.com", "name": "Info Azienda"}
                                    ],
                                    "last_message_date": "2025-01-02T16:00:00+00:00",
                                    "is_unread": False,
                                    "labels": ["INBOX", "IMPORTANT", "SENT", "DRAFT"]
                                }
                            ]
                        },
                        "microsoft_thread": {
                            "summary": "Thread Microsoft Outlook",
                            "value": [
                                {
                                    "id": "AAMkAGI2...",
                                    "subject": "Riunione settimanale",
                                    "snippet": "Confermo partecipazione alla riunione...",
                                    "messages": [
                                        {
                                            "id": "AAMkAGI2msg1...",
                                            "subject": "Riunione settimanale",
                                            "snippet": "Buongiorno a tutti...",
                                            "body_text": None,
                                            "body_html": "<html><body>Buongiorno a tutti...</body></html>",
                                            "from_address": {
                                                "email": "manager@company.com",
                                                "name": "Project Manager"
                                            },
                                            "to_addresses": [
                                                {"email": "team@company.com", "name": "Team"}
                                            ],
                                            "cc_addresses": [],
                                            "bcc_addresses": [],
                                            "date": "2025-01-02T09:00:00+00:00",
                                            "is_read": True,
                                            "is_draft": False,
                                            "attachments": [{"filename": "attachment", "mime_type": None, "size": None}],
                                            "labels": ["meeting", "weekly"]
                                        }
                                    ],
                                    "message_count": 1,
                                    "has_drafts": False,
                                    "has_attachments": True,
                                    "participants": [
                                        {"email": "manager@company.com", "name": "Project Manager"},
                                        {"email": "team@company.com", "name": "Team"}
                                    ],
                                    "last_message_date": "2025-01-02T09:00:00+00:00",
                                    "is_unread": False,
                                    "labels": ["meeting", "weekly"]
                                }
                            ]
                        },
                        "imap_thread": {
                            "summary": "Thread IMAP",
                            "value": [
                                {
                                    "id": "12345",
                                    "subject": "Preventivo richiesto",
                                    "snippet": "In allegato il preventivo richiesto...",
                                    "messages": [
                                        {
                                            "id": "12345",
                                            "subject": "Preventivo richiesto",
                                            "snippet": "Buongiorno, richiedo preventivo...",
                                            "body_text": "Buongiorno,\n\nRichiedo preventivo per...",
                                            "body_html": None,
                                            "from_address": {
                                                "email": "cliente@mail.it",
                                                "name": None
                                            },
                                            "to_addresses": [
                                                {"email": "vendite@azienda.it", "name": None}
                                            ],
                                            "cc_addresses": [],
                                            "bcc_addresses": [],
                                            "date": "2025-01-02T08:00:00+00:00",
                                            "is_read": False,
                                            "is_draft": False,
                                            "attachments": [],
                                            "labels": []
                                        }
                                    ],
                                    "message_count": 1,
                                    "has_drafts": False,
                                    "has_attachments": False,
                                    "participants": [
                                        {"email": "cliente@mail.it", "name": None},
                                        {"email": "vendite@azienda.it", "name": None}
                                    ],
                                    "last_message_date": "2025-01-02T08:00:00+00:00",
                                    "is_unread": True,
                                    "labels": []
                                }
                            ]
                        }
                    }
                }
            }
        },
        400: {
            "description": "Richiesta non valida - parametri mancanti o non validi",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_provider": {
                            "summary": "Provider mancante",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campi obbligatori mancanti: provider"
                            }
                        },
                        "invalid_provider": {
                            "summary": "Provider non valido",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campo 'provider' non valido: deve essere 'google', 'microsoft' o 'imap'"
                            }
                        },
                        "missing_imap_fields": {
                            "summary": "Campi IMAP mancanti",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campi obbligatori mancanti: imap_server, imap_port, email, password"
                            }
                        },
                        "invalid_date": {
                            "summary": "Formato data non valido",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campo 'time_min' non valido: formato data/ora non valido. Utilizzare formato ISO 8601 (es. 2025-01-15T10:00:00Z)"
                            }
                        },
                        "invalid_max_results": {
                            "summary": "max_results non valido",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campo 'max_results' non valido: deve essere un intero tra 1 e 500"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Token non valido o scaduto",
            "content": {
                "application/json": {
                    "examples": {
                        "google_token": {
                            "summary": "Token Google non valido",
                            "value": {
                                "error": True,
                                "status_code": 401,
                                "detail": "Token Google non valido"
                            }
                        },
                        "microsoft_token": {
                            "summary": "Token Microsoft non valido",
                            "value": {
                                "error": True,
                                "status_code": 401,
                                "detail": "Token Microsoft non valido"
                            }
                        },
                        "imap_auth": {
                            "summary": "Credenziali IMAP non valide",
                            "value": {
                                "error": True,
                                "status_code": 401,
                                "detail": "Credenziali IMAP non valide"
                            }
                        }
                    }
                }
            }
        },
        502: {
            "description": "Errore di comunicazione con il servizio esterno",
            "content": {
                "application/json": {
                    "examples": {
                        "gmail_error": {
                            "summary": "Errore Gmail API",
                            "value": {
                                "error": True,
                                "status_code": 502,
                                "detail": "Errore servizio Gmail: Status code 403: Forbidden"
                            }
                        },
                        "microsoft_error": {
                            "summary": "Errore Microsoft Graph",
                            "value": {
                                "error": True,
                                "status_code": 502,
                                "detail": "Errore servizio Microsoft Graph: Timeout durante la richiesta"
                            }
                        },
                        "imap_error": {
                            "summary": "Errore connessione IMAP",
                            "value": {
                                "error": True,
                                "status_code": 502,
                                "detail": "Errore servizio IMAP (imap.example.com): Connection refused"
                            }
                        }
                    }
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 500,
                        "detail": "Errore interno del server"
                    }
                }
            }
        }
    }
)
async def get_email_threads(
    request_data: Dict[str, Any] = Body(
        ...,
        examples={
            "google": {
                "summary": "Richiesta Gmail",
                "description": "Recupera thread da Gmail con filtri temporali",
                "value": {
                    "provider": "google",
                    "token": "ya29.a0AfH6SMBx...",
                    "time_min": "2025-01-01T00:00:00Z",
                    "time_max": "2025-01-31T23:59:59Z",
                    "max_results": 50,
                    "include_drafts": True,
                    "include_spam_trash": False,
                    "query": "is:unread"
                }
            },
            "microsoft": {
                "summary": "Richiesta Microsoft",
                "description": "Recupera thread da Outlook con filtri",
                "value": {
                    "provider": "microsoft",
                    "token": "eyJ0eXAiOiJKV1Q...",
                    "time_min": "2025-01-01T00:00:00Z",
                    "time_max": "2025-01-31T23:59:59Z",
                    "max_results": 50,
                    "include_drafts": True,
                    "folder": "inbox"
                }
            },
            "imap": {
                "summary": "Richiesta IMAP",
                "description": "Recupera thread via IMAP con credenziali",
                "value": {
                    "provider": "imap",
                    "imap_server": "imap.example.com",
                    "imap_port": 993,
                    "email": "user@example.com",
                    "password": "encrypted_password_token",
                    "time_min": "2025-01-01T00:00:00Z",
                    "time_max": "2025-01-31T23:59:59Z",
                    "max_results": 50,
                    "include_drafts": True,
                    "folder": "INBOX"
                }
            }
        }
    )
):
    """
    Recupera i thread di conversazioni email dalla casella di posta.
    
    Supporta Gmail, Microsoft Outlook e IMAP con un'interfaccia unificata.
    Include automaticamente i draft associati ai thread.
    """
    return await controller.get_email_threads(request_data)
