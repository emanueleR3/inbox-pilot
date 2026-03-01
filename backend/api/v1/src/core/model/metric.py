from pydantic import BaseModel, Field
from typing import Optional, List


class MetricMetadata(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    service_id: Optional[str] = None


class OverviewMetrics(BaseModel):
    ticket_total: int
    ticket_automatizzati: int
    deflection_rate_pct: float
    avg_response_time_seconds: float
    alert_attivi: int
    metadata: MetricMetadata


class AiVsHumanBreakdown(BaseModel):
    human_response: bool
    count: int


class DeflectionTrendItem(BaseModel):
    day: str
    deflection_pct: float


class DeflectionByCategoryItem(BaseModel):
    category: Optional[str]
    deflection_pct: float


class AutomationMetrics(BaseModel):
    ai_vs_human: List[AiVsHumanBreakdown]
    deflection_trend: List[DeflectionTrendItem]
    deflection_by_category: List[DeflectionByCategoryItem]
    metadata: MetricMetadata


class OutcomeDistributionItem(BaseModel):
    outcome: Optional[str]
    count: int


class ScoreByOutcomeItem(BaseModel):
    outcome: Optional[str]
    avg_score: float
    feedback_count: Optional[int] = None


class AiQualityMetrics(BaseModel):
    outcome_distribution: List[OutcomeDistributionItem]
    success_rate_pct: float
    pct_negative_feedback: float
    avg_score_by_outcome: List[ScoreByOutcomeItem]
    metadata: MetricMetadata


class PriorityThread(BaseModel):
    thread_id: str
    priority_score: float
    processed_at: str


class RiskMetrics(BaseModel):
    num_ticket_critici: int
    ticket_critici_list: List[PriorityThread]
    priority_alerts: List[PriorityThread]
    avg_time_to_first_ai_seconds: float
    metadata: MetricMetadata


class ThreadsByCategoryItem(BaseModel):
    category: Optional[str]
    count: int


class AttachmentStats(BaseModel):
    count: int


class UsageMetrics(BaseModel):
    email_processate: int
    email_per_giorno: List
    total_minutes_processed: float
    thread_attivi: int
    threads_per_category: List[ThreadsByCategoryItem]
    attachments: AttachmentStats
    metadata: MetricMetadata


class EventsByTypeItem(BaseModel):
    event_type: Optional[str]
    count: int


class EventTrendItem(BaseModel):
    day: str
    count: int


class EventMetrics(BaseModel):
    totale_eventi: int
    eventi_creati_ai: int
    eventi_creati_umano: int
    ai_pct: float
    eventi_per_tipo: List[EventsByTypeItem]
    trend: List[EventTrendItem]
    metadata: MetricMetadata

