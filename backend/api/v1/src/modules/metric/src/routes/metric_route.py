# app/routes/metrics_routes.py
from fastapi import APIRouter, Query
from typing import Optional
from controllers.metric_controller import MetricsController

router = APIRouter(prefix="/metrics", tags=["metrics"])
controller = MetricsController()


@router.get(
    "/overview",
    summary="KPI overview",
    description="Restituisce una panoramica delle metriche KPI principali per un abbonamento, inclusi ticket totali, ticket automatizzati, deflection rate, tempo medio di risposta, CSAT medio e alert attivi.",
    responses={
        200: {
            "description": "Metriche KPI recuperate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "ticket_total": 150,
                        "ticket_automatizzati": 120,
                        "deflection_rate_pct": 80.0,
                        "avg_response_time_seconds": 45.5,
                        "csat_medio": 4.2,
                        "alert_attivi": 3,
                        "metadata": {
                            "date_from": "2025-01-01T00:00:00",
                            "date_to": "2025-01-31T23:59:59",
                            "subscription_id": "sub_12345"
                        }
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {"detail": "subscription_id richiesto"}
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore overview: <dettaglio errore>"}
                }
            }
        }
    },
)
async def get_overview(
    subscription_id: str = Query(..., description="ID della sottoscrizione"),
    date_from: Optional[str] = Query(None, description="Data inizio in formato ISO (es. 2025-01-01T00:00:00)"),
    date_to: Optional[str] = Query(None, description="Data fine in formato ISO (es. 2025-01-31T23:59:59)"),
):
    return await controller.get_overview_metrics(subscription_id, date_from, date_to)


@router.get(
    "/automation",
    summary="Automation metrics",
    description="Restituisce le metriche di automazione per un abbonamento, inclusi breakdown AI vs human, deflection trend giornaliero, deflection per categoria e media messaggi per thread.",
    responses={
        200: {
            "description": "Metriche di automazione recuperate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "ai_vs_human": [
                            {"human_response": "false", "count": 120},
                            {"human_response": "true", "count": 30}
                        ],
                        "deflection_trend": [
                            {"day": "2025-01-01", "deflection_pct": 78.5},
                            {"day": "2025-01-02", "deflection_pct": 82.3}
                        ],
                        "deflection_by_category": [
                            {"category": "Supporto", "deflection_pct": 85.0},
                            {"category": "Vendite", "deflection_pct": 72.0}
                        ],
                        "avg_messages_per_thread": 3.5,
                        "metadata": {
                            "date_from": "2025-01-01T00:00:00",
                            "date_to": "2025-01-31T23:59:59"
                        }
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {"detail": "subscription_id richiesto"}
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore automation: <dettaglio errore>"}
                }
            }
        }
    },
)
async def get_automation(
    subscription_id: str = Query(..., description="ID della sottoscrizione"),
    date_from: Optional[str] = Query(None, description="Data inizio in formato ISO"),
    date_to: Optional[str] = Query(None, description="Data fine in formato ISO"),
):
    return await controller.get_automation_metrics(subscription_id, date_from, date_to)


@router.get(
    "/ai-quality",
    summary="AI quality metrics",
    description="Restituisce le metriche di qualità AI per un abbonamento, inclusi distribuzione outcome, success rate, distribuzione CSAT, percentuale feedback negativi e score medio per outcome.",
    responses={
        200: {
            "description": "Metriche qualità AI recuperate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "outcome_distribution": [
                            {"outcome": "success", "count": 100},
                            {"outcome": "failure", "count": 5}
                        ],
                        "success_rate_pct": 95.24,
                        "csat_distribution": [
                            {"score": 5, "count": 80},
                            {"score": 4, "count": 15}
                        ],
                        "pct_negative_feedback": 2.5,
                        "avg_score_by_outcome": [
                            {"outcome": "success", "avg_score": 4.5, "feedback_count": 90}
                        ],
                        "metadata": {
                            "date_from": "2025-01-01T00:00:00",
                            "date_to": "2025-01-31T23:59:59"
                        }
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {"detail": "subscription_id richiesto"}
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore ai-quality: <dettaglio errore>"}
                }
            }
        }
    },
)
async def get_ai_quality(
    subscription_id: str = Query(..., description="ID della sottoscrizione"),
    date_from: Optional[str] = Query(None, description="Data inizio in formato ISO"),
    date_to: Optional[str] = Query(None, description="Data fine in formato ISO"),
):
    return await controller.get_ai_quality_metrics(subscription_id, date_from, date_to)


@router.get(
    "/risk",
    summary="Risk & alerting metrics",
    description="Restituisce le metriche di rischio e alerting per un abbonamento, inclusi numero ticket critici, lista ticket critici, priority alerts e tempo medio alla prima risposta AI.",
    responses={
        200: {
            "description": "Metriche di rischio recuperate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "num_ticket_critici": 5,
                        "ticket_critici_list": [
                            {
                                "thread_id": "th_001",
                                "subject": "Problema urgente",
                                "sender_email": "cliente@example.com",
                                "last_message_at": "2025-01-15T10:30:00",
                                "category": "Supporto",
                                "subcategory": "Tecnico",
                                "summary": "Cliente bloccato"
                            }
                        ],
                        "priority_alerts": [
                            {"thread_id": "th_002", "subject": "Alta priorità", "priority_score": 0.95}
                        ],
                        "avg_time_to_first_ai_seconds": 120.5,
                        "metadata": {
                            "date_from": "2025-01-01T00:00:00",
                            "date_to": "2025-01-31T23:59:59"
                        }
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {"detail": "subscription_id richiesto"}
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore risk: <dettaglio errore>"}
                }
            }
        }
    },
)
async def get_risk(
    subscription_id: str = Query(..., description="ID della sottoscrizione"),
    date_from: Optional[str] = Query(None, description="Data inizio in formato ISO"),
    date_to: Optional[str] = Query(None, description="Data fine in formato ISO"),
):
    return await controller.get_risk_metrics(subscription_id, date_from, date_to)


@router.get(
    "/usage",
    summary="Usage & billing metrics",
    description="Restituisce le metriche di utilizzo e billing per un abbonamento, inclusi email processate, email per giorno, minuti totali processati, thread attivi, threads per categoria e statistiche allegati.",
    responses={
        200: {
            "description": "Metriche di utilizzo recuperate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "email_processate": 500,
                        "email_per_giorno": [
                            {"day": "2025-01-01", "count": 25},
                            {"day": "2025-01-02", "count": 30}
                        ],
                        "total_minutes_processed": 150.5,
                        "thread_attivi": 45,
                        "threads_per_category": [
                            {"category": "Supporto", "count": 30},
                            {"category": "Vendite", "count": 15}
                        ],
                        "attachments": {
                            "pct_threads_with_attachments": 25.5,
                            "avg_attachment_size_bytes": 102400
                        },
                        "metadata": {
                            "date_from": "2025-01-01T00:00:00",
                            "date_to": "2025-01-31T23:59:59"
                        }
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {"detail": "subscription_id richiesto"}
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore usage: <dettaglio errore>"}
                }
            }
        }
    },
)
async def get_usage(
    subscription_id: str = Query(..., description="ID della sottoscrizione"),
    date_from: Optional[str] = Query(None, description="Data inizio in formato ISO"),
    date_to: Optional[str] = Query(None, description="Data fine in formato ISO"),
):
    return await controller.get_usage_metrics(subscription_id, date_from, date_to)


@router.get(
    "/events",
    summary="Calendar / events metrics",
    description="Restituisce le metriche relative agli eventi calendario per un abbonamento, inclusi totale eventi, eventi creati da AI, eventi creati da umani, percentuale AI, eventi per tipo e trend.",
    responses={
        200: {
            "description": "Metriche eventi recuperate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "totale_eventi": 100,
                        "eventi_creati_ai": 75,
                        "eventi_creati_umano": 25,
                        "ai_pct": 75.0,
                        "eventi_per_tipo": [
                            {"event_type": "meeting", "count": 60},
                            {"event_type": "call", "count": 40}
                        ],
                        "trend": [
                            {"day": "2025-01-01", "count": 5},
                            {"day": "2025-01-02", "count": 8}
                        ],
                        "metadata": {
                            "date_from": "2025-01-01T00:00:00",
                            "date_to": "2025-01-31T23:59:59"
                        }
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {"detail": "subscription_id richiesto"}
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore events: <dettaglio errore>"}
                }
            }
        }
    },
)
async def get_events(
    subscription_id: str = Query(..., description="ID della sottoscrizione"),
    date_from: Optional[str] = Query(None, description="Data inizio in formato ISO"),
    date_to: Optional[str] = Query(None, description="Data fine in formato ISO"),
):
    return await controller.get_event_metrics(subscription_id, date_from, date_to)
