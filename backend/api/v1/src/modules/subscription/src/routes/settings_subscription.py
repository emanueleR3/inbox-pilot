from fastapi import APIRouter, Body, Depends, status
from src.core.dependecy import get_current_user
from src.modules.subscription.src.controllers.subscription_controller import SubscriptionController

router = APIRouter(
    dependencies=[Depends(get_current_user)],
    tags=["Settings Subscription"],
)

controller = SubscriptionController()

@router.get(
    "/{subscription_id}",
    summary="Recupera una sottoscrizione per ID",
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
                        "current_period_end": "2025-12-31T23:59:59Z",
                        "plan": "premium",
                        "website": "https://www.acme.it",
                        "industry": "Tecnologia",
                        "employee_count": 50,
                        "products_service": "Software development",
                        "tone_of_voice": "Professionale",
                        "signature": "Cordiali saluti, Team ACME",
                        "phone_number": "+39 02 1234567"
                    }
                }
            }
        },
        400: {"description": "ID sottoscrizione mancante"},
        404: {"description": "Sottoscrizione non trovata"},
        500: {"description": "Errore interno del server"}
    }
)
def get_subscription_by_id(subscription_id: str):
    subscription = controller.get_subscription_by_id(subscription_id)
    return subscription


@router.patch(
    "/{subscription_id}",
    summary="Aggiorna una sottoscrizione esistente",
    description="""
    Aggiorna parzialmente una sottoscrizione esistente. 
    È possibile inviare solo i campi che si desidera modificare.
    
    **Campi aggiornabili:**
    - name: Nome della sottoscrizione
    - vat_number: Partita IVA
    - city: Città
    - address: Indirizzo
    - active: Stato attivo
    - current_period_end: Data di fine periodo corrente
    - plan: Piano di sottoscrizione
    - website: Sito web
    - industry: Settore industriale
    - employee_count: Numero dipendenti
    - products_service: Prodotti/servizi offerti
    - tone_of_voice: Tono di voce per le comunicazioni
    - signature: Firma per le email
    - phone_number: Numero di telefono
    """,
    responses={
        200: {
            "description": "Sottoscrizione aggiornata con successo",
            "content": {
                "application/json": {
                    "example": {
                        "subscription_id": "d7a8dfe2-47af-4c98-a02c-2fcb49c4716c",
                        "name": "ACME S.r.l. - Aggiornata",
                        "vat_number": "IT123456789",
                        "city": "Milano",
                        "address": "Via Roma 1",
                        "active": True,
                        "current_period_end": "2026-12-31T23:59:59Z",
                        "plan": "enterprise",
                        "website": "https://www.acme.it",
                        "industry": "Tecnologia",
                        "employee_count": 75,
                        "products_service": "Software development",
                        "tone_of_voice": "Professionale",
                        "signature": "Cordiali saluti, Team ACME",
                        "phone_number": "+39 02 1234567"
                    }
                }
            }
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "examples": {
                        "no_fields": {
                            "value": {"detail": "Nessun campo da aggiornare"}
                        },
                        "invalid_data": {
                            "value": {"detail": "Dati non validi"}
                        }
                    }
                }
            }
        },
        404: {"description": "Sottoscrizione non trovata"},
        500: {"description": "Errore interno del server"}
    }
)
def update_subscription(
    subscription_id: str,
    payload: dict = Body(
        ...,
        example={
            "name": "ACME S.r.l. - Aggiornata",
            "plan": "enterprise",
            "employee_count": 75,
            "current_period_end": "2026-12-31T23:59:59Z"
        },
        description="Campi della sottoscrizione da aggiornare. Inviare solo i campi che si desidera modificare.",
    )
):
    subscription = controller.update_subscription(subscription_id, payload)
    return subscription