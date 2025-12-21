from fastapi import APIRouter, Body, Depends, status
from src.core.dependecy import get_current_user
from src.modules.quiz_session.src.controllers.quiz_controller import QuizController

router = APIRouter(
    #dependencies=[Depends(get_current_user)],
    tags=["Quiz session"],
)
controller = QuizController()


@router.patch(
    "/update-final-markdown",
    status_code=status.HTTP_200_OK,
    summary="Aggiorna il final_markdown di una sessione quiz",
    description="""
    Aggiorna il campo final_markdown di una sessione quiz esistente identificata dal session_id.
    
    Il final_markdown contiene il report finale del quiz in formato Markdown, includendo
    statistiche, risultati e eventuali feedback per l'utente.
    
    **Parametri richiesti:**
    - `session_id`: ID univoco della sessione quiz da aggiornare
    - `final_markdown`: Nuovo contenuto in formato Markdown
    
    **Possibili errori:**
    - `400 Bad Request`: Parametri mancanti o non validi
    - `404 Not Found`: Sessione quiz non trovata
    - `500 Internal Server Error`: Errore durante l'aggiornamento del database
    """,
    responses={
        200: {
            "description": "Final markdown aggiornato con successo",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Final markdown aggiornato con successo",
                        "data": {
                            "session_id": "550e8400-e29b-41d4-a716-446655440000",
                            "final_markdown": "# Quiz Completato\n\nScore: 80%",
                            "updated_at": "2025-12-21T10:30:00Z"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Richiesta non valida - Campi mancanti o non validi",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_fields": {
                            "summary": "Campi obbligatori mancanti",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campi obbligatori mancanti: session_id, final_markdown"
                            }
                        },
                        "invalid_field": {
                            "summary": "Campo non valido",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "session_id deve essere una stringa non vuota"
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "Sessione quiz non trovata",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 404,
                        "detail": "Sessione quiz con ID 'xyz' non trovata"
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
                        "detail": "Errore database durante: aggiornamento final_markdown"
                    }
                }
            }
        }
    }
)
def update_final_markdown(
    payload: dict = Body(
        ...,
        description="Dati per l'aggiornamento del final_markdown",
        examples=[{
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "final_markdown": "# Quiz Risultati\n\n## Riepilogo\n- Domande totali: 10\n- Risposte corrette: 8\n- Score: 80%"
        }]
    )
) -> dict:
    updated_session = controller.update_final_markdown(payload)
    
    return {
        "success": True,
        "message": "Final markdown aggiornato con successo",
        "data": updated_session
    }


