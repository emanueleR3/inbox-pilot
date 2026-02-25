# app/routes/metrics_routes.py
from fastapi import APIRouter, Depends, Path
from typing import Optional
from api.v1.src.core.dependecy import get_current_user
from src.modules.metric.src.controllers.metric_controller import MetricsController

router = APIRouter(
    dependencies=[Depends(get_current_user)],
    tags=["Metrics"]
)
controller = MetricsController()

@router.get(
    "/overview/{subscription_id}",
    summary="KPI overview",
    description=(
        "Restituisce le metriche KPI principali del periodo: ticket totali, ticket automatizzati (gestiti solo da AI), "
        "deflection rate (% ticket senza intervento umano), tempo medio di risposta AI, e alert attivi (priority_score > 0.8). "
        "Queste metriche sono indicate per KPI cards."
    ),
    responses={
        200: {
            "description": "Metriche KPI recuperate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "ticket_total": 33,
                        "ticket_automatizzati": 24,
                        "deflection_rate_pct": 72.73,
                        "avg_response_time_seconds": 0.0,
                        "alert_attivi": 1,
                        "metadata": {
                            "date_from": "2025-11-13T00:28:39.810576",
                            "date_to": "2025-12-13T00:28:39.810576",
                            "subscription_id": "8e798771-1995-4a5e-acfe-76caf64c1989"
                        }
                    }
                }
            }
        }
    }
)
async def get_overview(subscription_id: str, date_from: str | None = None, date_to: str | None = None):
    return await controller.get_overview_metrics(subscription_id, date_from, date_to)


@router.get(
    "/automation/{subscription_id}",
    summary="Automation metrics",
    description=(
        "Restituisce le metriche di automazione: breakdown AI vs umani (donut chart consigliato), deflection trend giornaliero (line chart), "
        "e deflection per categoria (horizontal bar chart)."
    ),
    responses={
        200: {
            "description": "Metriche di automazione recuperate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "ai_vs_human": [
                            {"human_response": True, "count": 9},
                            {"human_response": False, "count": 24}
                        ],
                        "deflection_trend": [
                            {"day": "2025-12-05", "deflection_pct": 33.33},
                            {"day": "2025-12-06", "deflection_pct": 55.56}
                        ],
                        "deflection_by_category": [
                            {"category": "INFO_PROVIDED", "deflection_pct": 66.67},
                            {"category": "PROMOTION", "deflection_pct": 100.0}
                        ],
                        "metadata": {
                            "date_from": "2025-11-13T00:29:02.865547",
                            "date_to": "2025-12-13T00:29:02.865547",
                            "subscription_id": "8e798771-1995-4a5e-acfe-76caf64c1989"
                        }
                    }
                }
            }
        }
    }
)
async def get_automation(subscription_id: str, date_from: str | None = None, date_to: str | None = None):
    return await controller.get_automation_metrics(subscription_id, date_from, date_to)


@router.get(
    "/ai-quality/{subscription_id}",
    summary="AI quality metrics",
    description=(
        "Restituisce le metriche di qualità AI: distribuzione degli outcome (donut chart), success rate (KPI card), "
        "percentuale feedback negativi, e score medio per tipo di outcome (bar chart)."
    ),
    responses={
        200: {
            "description": "Metriche qualità AI recuperate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "outcome_distribution": [
                            {"outcome": "SENT", "count": 26},
                            {"outcome": "DRAFT", "count": 8}
                        ],
                        "success_rate_pct": 0.0,
                        "pct_negative_feedback": 0.0,
                        "avg_score_by_outcome": [],
                        "metadata": {
                            "date_from": "2025-11-13T00:29:31.479973",
                            "date_to": "2025-12-13T00:29:31.479973",
                            "subscription_id": "8e798771-1995-4a5e-acfe-76caf64c1989"
                        }
                    }
                }
            }
        }
    }
)
async def get_ai_quality(subscription_id: str, date_from: str | None = None, date_to: str | None = None):
    return await controller.get_ai_quality_metrics(subscription_id, date_from, date_to)


@router.get(
    "/risk/{subscription_id}",
    summary="Risk & alerting metrics",
    description=(
        "Restituisce le metriche di rischio: numero ticket critici (priority_score > 0.8), lista dettagliata ticket critici, "
        "e priority alerts (tabella consigliata)."
    ),
    responses={
        200: {
            "description": "Metriche di rischio recuperate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "num_ticket_critici": 1,
                        "ticket_critici_list": [
                            {"thread_id": "fbdae168-d652-4d63-af5c-f9b70afee0c0", "priority_score": 0.9, "processed_at": "2025-12-09T16:04:18.952465+00:00"}
                        ],
                        "priority_alerts": [
                            {"thread_id": "fbdae168-d652-4d63-af5c-f9b70afee0c0", "priority_score": 0.9, "processed_at": "2025-12-09T16:04:18.952465+00:00"}
                        ],
                        "avg_time_to_first_ai_seconds": 0.0,
                        "metadata": {
                            "date_from": "2025-11-13T00:29:54.909899",
                            "date_to": "2025-12-13T00:29:54.909899",
                            "subscription_id": "8e798771-1995-4a5e-acfe-76caf64c1989"
                        }
                    }
                }
            }
        }
    }
)
async def get_risk(subscription_id: str, date_from: str | None = None, date_to: str | None = None):
    return await controller.get_risk_metrics(subscription_id, date_from, date_to)


@router.get(
    "/usage/{subscription_id}",
    summary="Usage & billing metrics",
    description=(
        "Restituisce le metriche di utilizzo: email processate (line chart), minuti totali processati, thread attivi, "
        "thread per categoria (bar chart), e statistiche allegati."
    ),
    responses={
        200: {
            "description": "Metriche di utilizzo recuperate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "email_processate": 34,
                        "email_per_giorno": [],
                        "total_minutes_processed": 0.17,
                        "thread_attivi": 33,
                        "threads_per_category": [
                            {"category": "INFO_PROVIDED", "count": 3},
                            {"category": "PROMOTION", "count": 6}
                        ],
                        "attachments": {"count": 7},
                        "metadata": {
                            "date_from": "2025-11-13T00:30:16.164398",
                            "date_to": "2025-12-13T00:30:16.164398",
                            "subscription_id": "8e798771-1995-4a5e-acfe-76caf64c1989"
                        }
                    }
                }
            }
        }
    }
)
async def get_usage(subscription_id: str, date_from: str | None = None, date_to: str | None = None):
    return await controller.get_usage_metrics(subscription_id, date_from, date_to)


@router.get(
    "/events/{subscription_id}",
    summary="Calendar / events metrics",
    description=(
        "Restituisce le metriche eventi calendario: totale eventi, eventi creati da AI vs umani (stacked bar), "
        "percentuale AI (KPI card), eventi per tipo (bar chart), e trend giornaliero (line chart)."
    ),
    responses={
        200: {
            "description": "Metriche eventi recuperate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "totale_eventi": 3,
                        "eventi_creati_ai": 0,
                        "eventi_creati_umano": 3,
                        "ai_pct": 0.0,
                        "eventi_per_tipo": [{"event_type": "APPOINTMENT", "count": 3}],
                        "trend": [
                            {"day": "2025-12-05", "count": 1},
                            {"day": "2025-12-06", "count": 1}
                        ],
                        "metadata": {
                            "date_from": "2025-11-13T00:30:41.979829",
                            "date_to": "2025-12-13T00:30:41.979829",
                            "subscription_id": "8e798771-1995-4a5e-acfe-76caf64c1989"
                        }
                    }
                }
            }
        }
    }
)
async def get_events(subscription_id: str, date_from: str | None = None, date_to: str | None = None):
    return await controller.get_event_metrics(subscription_id, date_from, date_to)
