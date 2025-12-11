# app/models/metrics_models.py
"""
Modelli Pydantic per le risposte delle API delle metriche.
Definisce i tipi di dati per tutte le metriche esposte dall'applicazione.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class Meta(BaseModel):
    """Metadati comuni a tutte le risposte delle metriche."""
    date_from: Optional[str] = Field(None, description="Data di inizio del periodo analizzato (ISO format)")
    date_to: Optional[str] = Field(None, description="Data di fine del periodo analizzato (ISO format)")
    subscription_id: Optional[str] = Field(None, description="ID della sottoscrizione")


# --- Overview Models ---

class OverviewResponse(BaseModel):
    """Risposta per le metriche di overview KPI."""
    ticket_total: int = Field(..., description="Numero totale di ticket nel periodo")
    ticket_automatizzati: int = Field(..., description="Numero di ticket gestiti automaticamente dall'AI")
    deflection_rate_pct: float = Field(..., description="Percentuale di deflection (ticket automatizzati/totali * 100)")
    avg_response_time_seconds: float = Field(..., description="Tempo medio di risposta in secondi")
    csat_medio: Optional[float] = Field(None, description="Punteggio CSAT medio (Customer Satisfaction)")
    alert_attivi: int = Field(..., description="Numero di alert attualmente attivi")
    metadata: Meta = Field(..., description="Metadati della richiesta")


# --- Automation Models ---

class AutomationMetricItem(BaseModel):
    """Singolo elemento del breakdown AI vs Human."""
    human_response: str = Field(..., description="Indica se la risposta è stata umana ('true'/'false')")
    count: int = Field(..., description="Numero di occorrenze")


class DeflectionTrendItem(BaseModel):
    """Singolo elemento del trend di deflection giornaliero."""
    day: str = Field(..., description="Data nel formato ISO (es. '2025-01-01')")
    deflection_pct: float = Field(..., description="Percentuale di deflection per il giorno")


class DeflectionByCategoryItem(BaseModel):
    """Singolo elemento della deflection per categoria."""
    category: Optional[str] = Field(None, description="Nome della categoria")
    deflection_pct: float = Field(..., description="Percentuale di deflection per la categoria")


class AutomationResponse(BaseModel):
    """Risposta per le metriche di automazione."""
    ai_vs_human: List[AutomationMetricItem] = Field(..., description="Breakdown ticket gestiti da AI vs umano")
    deflection_trend: List[DeflectionTrendItem] = Field(..., description="Trend giornaliero della deflection")
    deflection_by_category: List[DeflectionByCategoryItem] = Field(..., description="Deflection suddivisa per categoria")
    avg_messages_per_thread: float = Field(..., description="Media messaggi per thread")
    metadata: Meta = Field(..., description="Metadati della richiesta")


# --- AI Quality Models ---

class OutcomeDistributionItem(BaseModel):
    """Singolo elemento della distribuzione degli outcome."""
    outcome: Optional[str] = Field(None, description="Tipo di outcome (es. 'success', 'failure')")
    count: int = Field(..., description="Numero di occorrenze")


class CSATDistributionItem(BaseModel):
    """Singolo elemento della distribuzione dei punteggi CSAT."""
    score: Optional[int] = Field(None, description="Punteggio CSAT (1-5)")
    count: int = Field(..., description="Numero di occorrenze")


class ScoreByOutcomeItem(BaseModel):
    """Score medio per tipo di outcome."""
    outcome: Optional[str] = Field(None, description="Tipo di outcome")
    avg_score: float = Field(..., description="Punteggio medio")
    feedback_count: Optional[int] = Field(None, description="Numero di feedback ricevuti")


class AIQualityResponse(BaseModel):
    """Risposta per le metriche di qualità AI."""
    outcome_distribution: List[OutcomeDistributionItem] = Field(..., description="Distribuzione degli outcome")
    success_rate_pct: float = Field(..., description="Tasso di successo in percentuale")
    csat_distribution: List[CSATDistributionItem] = Field(..., description="Distribuzione dei punteggi CSAT")
    pct_negative_feedback: float = Field(..., description="Percentuale di feedback negativi (score <= 2)")
    avg_score_by_outcome: List[ScoreByOutcomeItem] = Field(..., description="Score medio per tipo di outcome")
    metadata: Meta = Field(..., description="Metadati della richiesta")


# --- Risk Models ---

class CriticalTicketItem(BaseModel):
    """Singolo ticket critico."""
    thread_id: str = Field(..., description="ID del thread")
    subject: Optional[str] = Field(None, description="Oggetto del thread")
    sender_email: Optional[str] = Field(None, description="Email del mittente")
    last_message_at: Optional[str] = Field(None, description="Data ultimo messaggio (ISO format)")
    category: Optional[str] = Field(None, description="Categoria del ticket")
    subcategory: Optional[str] = Field(None, description="Sottocategoria del ticket")
    summary: Optional[str] = Field(None, description="Riepilogo del ticket")


class PriorityAlertItem(BaseModel):
    """Singolo alert di priorità."""
    thread_id: str = Field(..., description="ID del thread")
    subject: Optional[str] = Field(None, description="Oggetto del thread")
    priority_score: float = Field(..., description="Punteggio di priorità")


class RiskResponse(BaseModel):
    """Risposta per le metriche di rischio e alerting."""
    num_ticket_critici: int = Field(..., description="Numero di ticket con stato CRITICAL")
    ticket_critici_list: List[CriticalTicketItem] = Field(..., description="Lista dei ticket critici (max 100)")
    priority_alerts: List[PriorityAlertItem] = Field(..., description="Thread con priority score elevato")
    avg_time_to_first_ai_seconds: float = Field(..., description="Tempo medio alla prima risposta AI (secondi)")
    metadata: Meta = Field(..., description="Metadati della richiesta")


# --- Usage Models ---

class DailyEmailItem(BaseModel):
    """Email processate per singolo giorno."""
    day: str = Field(..., description="Data (ISO format)")
    count: int = Field(..., description="Numero di email processate")


class ThreadsByCategoryItem(BaseModel):
    """Thread suddivisi per categoria."""
    category: Optional[str] = Field(None, description="Nome della categoria")
    count: int = Field(..., description="Numero di thread")


class AttachmentStats(BaseModel):
    """Statistiche sugli allegati."""
    pct_threads_with_attachments: Optional[float] = Field(None, description="Percentuale di thread con allegati")
    avg_attachment_size_bytes: Optional[float] = Field(None, description="Dimensione media allegati in bytes")


class UsageResponse(BaseModel):
    """Risposta per le metriche di utilizzo e billing."""
    email_processate: int = Field(..., description="Numero totale di email processate")
    email_per_giorno: List[DailyEmailItem] = Field(..., description="Email processate per giorno")
    total_minutes_processed: float = Field(..., description="Minuti totali di processing")
    thread_attivi: int = Field(..., description="Numero di thread attivi nel periodo")
    threads_per_category: List[ThreadsByCategoryItem] = Field(..., description="Thread suddivisi per categoria")
    attachments: AttachmentStats = Field(..., description="Statistiche sugli allegati")
    metadata: Meta = Field(..., description="Metadati della richiesta")


# --- Event Models ---

class EventByTypeItem(BaseModel):
    """Eventi suddivisi per tipo."""
    event_type: Optional[str] = Field(None, description="Tipo di evento")
    count: int = Field(..., description="Numero di eventi")


class EventTrendItem(BaseModel):
    """Trend giornaliero degli eventi."""
    day: str = Field(..., description="Data (ISO format)")
    count: int = Field(..., description="Numero di eventi nel giorno")


class EventResponse(BaseModel):
    """Risposta per le metriche degli eventi calendario."""
    totale_eventi: int = Field(..., description="Numero totale di eventi nel periodo")
    eventi_creati_ai: int = Field(..., description="Numero di eventi creati dall'AI")
    eventi_creati_umano: int = Field(..., description="Numero di eventi creati manualmente")
    ai_pct: float = Field(..., description="Percentuale di eventi creati dall'AI")
    eventi_per_tipo: List[EventByTypeItem] = Field(..., description="Eventi suddivisi per tipo")
    trend: List[EventTrendItem] = Field(..., description="Trend giornaliero degli eventi")
    metadata: Meta = Field(..., description="Metadati della richiesta")
