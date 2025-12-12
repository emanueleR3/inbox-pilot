# app/routes/metrics_routes.py
from fastapi import APIRouter, Path
from typing import Optional
from src.modules.metric.src.controllers.metric_controller import MetricsController

router = APIRouter(tags=["Metrics"])
controller = MetricsController()


@router.get(
    "/overview/{subscription_id}",
    summary="KPI overview",
    description="Restituisce le metriche KPI principali: ticket totali, ticket automatizzati (gestiti solo da AI), "
                "deflection rate (% ticket senza intervento umano), tempo medio di risposta AI, e alert attivi (priority_score > 0.8).",
    responses={
        200: {"description": "Metriche KPI recuperate con successo"},
        400: {"description": "subscription_id non valido o mancante"},
        500: {"description": "Errore interno del server"}
    },
)
async def get_overview(
    subscription_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
):
    return await controller.get_overview_metrics(subscription_id, date_from, date_to)


@router.get(
    "/automation/{subscription_id}",
    summary="Automation metrics",
    description="Restituisce le metriche di automazione: breakdown AI vs umani, deflection trend giornaliero, "
                "e deflection per categoria.",
    responses={
        200: {"description": "Metriche di automazione recuperate con successo"},
        400: {"description": "subscription_id non valido o mancante"},
        500: {"description": "Errore interno del server"}
    },
)
async def get_automation(
    subscription_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
):
    return await controller.get_automation_metrics(subscription_id, date_from, date_to)


@router.get(
    "/ai-quality/{subscription_id}",
    summary="AI quality metrics",
    description="Restituisce le metriche di qualità AI: distribuzione outcome, success rate (% successo), "
                "e percentuale feedback negativi.",
    responses={
        200: {"description": "Metriche qualità AI recuperate con successo"},
        400: {"description": "subscription_id non valido o mancante"},
        500: {"description": "Errore interno del server"}
    },
)
async def get_ai_quality(
    subscription_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
):
    return await controller.get_ai_quality_metrics(subscription_id, date_from, date_to)


@router.get(
    "/risk/{subscription_id}",
    summary="Risk & alerting metrics",
    description="Restituisce le metriche di rischio: numero ticket critici (priority_score > 0.8), "
                "lista dettagliata ticket critici, e priority alerts.",
    responses={
        200: {"description": "Metriche di rischio recuperate con successo"},
        400: {"description": "subscription_id non valido o mancante"},
        500: {"description": "Errore interno del server"}
    },
)
async def get_risk(
    subscription_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
):
    return await controller.get_risk_metrics(subscription_id, date_from, date_to)


@router.get(
    "/usage/{subscription_id}",
    summary="Usage & billing metrics",
    description="Restituisce le metriche di utilizzo: email processate, minuti totali processati, "
                "thread attivi, thread per categoria, e statistiche allegati.",
    responses={
        200: {"description": "Metriche di utilizzo recuperate con successo"},
        400: {"description": "subscription_id non valido o mancante"},
        500: {"description": "Errore interno del server"}
    },
)
async def get_usage(
    subscription_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
):
    return await controller.get_usage_metrics(subscription_id, date_from, date_to)


@router.get(
    "/events/{subscription_id}",
    summary="Calendar / events metrics",
    description="Restituisce le metriche eventi calendario: totale eventi, eventi creati da AI vs umani, "
                "percentuale AI, eventi per tipo, e trend giornaliero.",
    responses={
        200: {"description": "Metriche eventi recuperate con successo"},
        400: {"description": "subscription_id non valido o mancante"},
        500: {"description": "Errore interno del server"}
    },
)
async def get_events(
    subscription_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
):
    return await controller.get_event_metrics(subscription_id, date_from, date_to)
