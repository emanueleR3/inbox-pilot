from typing import Dict, List
from src.core.database import get_supabase_client
from src.core.model.metric import (
    MetricMetadata,
    OverviewMetrics,
    AiVsHumanBreakdown,
    DeflectionTrendItem,
    DeflectionByCategoryItem,
    AutomationMetrics,
    OutcomeDistributionItem,
    AiQualityMetrics,
    PriorityThread,
    RiskMetrics,
    ThreadsByCategoryItem,
    AttachmentStats,
    UsageMetrics,
    EventsByTypeItem,
    EventTrendItem,
    EventMetrics
)


class MetricDAO:

    def __init__(self):
        self.supabase = get_supabase_client()

    def _get_service_emails(self, subscription_service_id: str) -> List[str]:
        rows = (
            self.supabase.table("subscription_services")
            .select("email")
            .eq("subscription_ser_id", subscription_service_id)
            .execute()
            .data
        ) or []
        return [r["email"] for r in rows if r.get("email")]

    def _get_service_ids(self, subscription_service_id: str) -> List[str]:
        rows = (
            self.supabase.table("subscription_services")
            .select("service_id")
            .eq("subscription_ser_id", subscription_service_id)
            .execute()
            .data
        ) or []
        return [r["service_id"] for r in rows if r.get("service_id")]

    async def get_overview_metrics(self, subscription_service_id: str, date_from: str, date_to: str) -> OverviewMetrics:
        emails = self._get_service_emails(subscription_service_id)

        if not emails:
            return OverviewMetrics(
                ticket_total=0,
                ticket_automatizzati=0,
                deflection_rate_pct=0,
                avg_response_time_seconds=0,
                alert_attivi=0,
                metadata=MetricMetadata(subscription_service_id=subscription_service_id, date_from=date_from, date_to=date_to)
            )

        threads = self.supabase.table("threads") \
            .select("human_response", "started_at") \
            .in_("box_email", emails) \
            .gte("started_at", date_from) \
            .lte("started_at", date_to) \
            .execute().data

        total = len(threads)
        ai_only = sum(1 for t in threads if not t["human_response"])

        ai_rows = (
            self.supabase.table("emails")
            .select("duration", "priority_score")
            .eq("ai_generated", True)
            .gte("datetime", date_from)
            .lte("datetime", date_to)
            .execute()
            .data
        ) or []

        durations = [r["duration"] for r in ai_rows if r.get("duration") is not None]
        avg_resp = (sum(durations) / len(durations)) if durations else 0
        alerts = sum(1 for r in ai_rows if (r.get("priority_score") is not None and r["priority_score"] > 0.8))

        return OverviewMetrics(
            ticket_total=total,
            ticket_automatizzati=ai_only,
            deflection_rate_pct=round((ai_only / total * 100) if total else 0, 2),
            avg_response_time_seconds=round(avg_resp, 2),
            alert_attivi=alerts,
            metadata=MetricMetadata(subscription_service_id=subscription_service_id, date_from=date_from, date_to=date_to)
        )

    async def get_automation_metrics(self, subscription_service_id: str, date_from: str, date_to: str) -> AutomationMetrics:
        emails = self._get_service_emails(subscription_service_id)

        threads = self.supabase.table("threads") \
            .select("human_response", "started_at", "category") \
            .in_("box_email", emails) \
            .gte("started_at", date_from) \
            .lte("started_at", date_to) \
            .execute().data

        ai_vs_human = [
            AiVsHumanBreakdown(human_response=True, count=sum(1 for t in threads if t["human_response"])),
            AiVsHumanBreakdown(human_response=False, count=sum(1 for t in threads if not t["human_response"]))
        ]

        trend: Dict[str, Dict[str, int]] = {}
        for t in threads:
            d = t["started_at"][:10]
            trend.setdefault(d, {"ai": 0, "total": 0})
            trend[d]["total"] += 1
            if not t["human_response"]:
                trend[d]["ai"] += 1

        deflection_trend = [
            DeflectionTrendItem(day=d, deflection_pct=(v["ai"] / v["total"] * 100 if v["total"] else 0))
            for d, v in trend.items()
        ]

        categories: Dict[str, Dict[str, int]] = {}
        for t in threads:
            c = t["category"]
            categories.setdefault(c, {"ai": 0, "total": 0})
            categories[c]["total"] += 1
            if not t["human_response"]:
                categories[c]["ai"] += 1

        deflection_by_category = [
            DeflectionByCategoryItem(category=c, deflection_pct=(v["ai"] / v["total"] * 100 if v["total"] else 0))
            for c, v in categories.items()
        ]

        return AutomationMetrics(
            ai_vs_human=ai_vs_human,
            deflection_trend=deflection_trend,
            deflection_by_category=deflection_by_category,
            metadata=MetricMetadata(subscription_service_id=subscription_service_id, date_from=date_from, date_to=date_to)
        )

    async def get_ai_quality_metrics(self, subscription_service_id: str, date_from: str, date_to: str) -> AiQualityMetrics:
        service_ids = self._get_service_ids(subscription_service_id)

        rows = self.supabase.table("emails") \
            .select("outcome") \
            .eq("ai_generated", True) \
            .in_("service_id", service_ids) \
            .gte("datetime", date_from) \
            .lte("datetime", date_to) \
            .execute().data

        dist: Dict[str, int] = {}
        for r in rows:
            dist[r["outcome"]] = dist.get(r["outcome"], 0) + 1

        success = dist.get("success", 0)
        total = len(rows)

        outcome_distribution = [
            OutcomeDistributionItem(outcome=o, count=c) for o, c in dist.items()
        ]

        return AiQualityMetrics(
            outcome_distribution=outcome_distribution,
            success_rate_pct=round((success / total * 100) if total else 0, 2),
            pct_negative_feedback=0,
            avg_score_by_outcome=[],
            metadata=MetricMetadata(subscription_service_id=subscription_service_id, date_from=date_from, date_to=date_to)
        )

    async def get_risk_metrics(self, subscription_service_id: str, date_from: str, date_to: str) -> RiskMetrics:
        service_ids = self._get_service_ids(subscription_service_id)

        rows = self.supabase.table("emails") \
            .select("thread_id", "priority_score", "datetime") \
            .eq("ai_generated", True) \
            .in_("service_id", service_ids) \
            .gte("datetime", date_from) \
            .lte("datetime", date_to) \
            .execute().data

        critical = [
            PriorityThread(
                thread_id=r["thread_id"],
                priority_score=r.get("priority_score"),
                processed_at=r.get("datetime")
            )
            for r in rows if (r.get("priority_score") is not None and r["priority_score"] > 0.8)
        ]

        return RiskMetrics(
            num_ticket_critici=len(critical),
            ticket_critici_list=critical,
            priority_alerts=critical,
            avg_time_to_first_ai_seconds=0,
            metadata=MetricMetadata(subscription_service_id=subscription_service_id, date_from=date_from, date_to=date_to)
        )

    async def get_usage_metrics(self, subscription_service_id: str, date_from: str, date_to: str) -> UsageMetrics:
        services = (
            self.supabase.table("subscription_services")
            .select("service_id", "email")
            .eq("subscription_service_id", subscription_service_id)
            .execute()
            .data
        ) or []

        service_ids = [s["service_id"] for s in services]
        emails = [s["email"] for s in services]

        email_rows = self.supabase.table("emails") \
            .select("email_id") \
            .eq("ai_generated", True) \
            .in_("service_id", service_ids) \
            .gte("datetime", date_from) \
            .lte("datetime", date_to) \
            .execute().data

        threads = self.supabase.table("threads") \
            .select("thread_id", "category") \
            .in_("box_email", emails) \
            .gte("started_at", date_from) \
            .lte("started_at", date_to) \
            .execute().data

        by_category: Dict[str, int] = {}
        for t in threads:
            by_category[t["category"]] = by_category.get(t["category"], 0) + 1

        attachments = (
            self.supabase.table("email_attachments")
            .select("size_bytes")
            .in_("service_id", service_ids)
            .execute()
            .data
        ) or []

        total_bytes = sum((a.get("size_bytes") or 0) for a in attachments)
        total_minutes = (total_bytes / 60000) if total_bytes else 0

        return UsageMetrics(
            email_processate=len(email_rows),
            email_per_giorno=[],
            total_minutes_processed=round(total_minutes, 2),
            thread_attivi=len(threads),
            threads_per_category=[
                ThreadsByCategoryItem(category=c, count=n) for c, n in by_category.items()
            ],
            attachments=AttachmentStats(count=len(attachments)),
            metadata=MetricMetadata(subscription_service_id=subscription_service_id, date_from=date_from, date_to=date_to)
        )

    async def get_event_metrics(self, subscription_service_id: str, date_from: str, date_to: str) -> EventMetrics:
        service_ids = self._get_service_ids(subscription_service_id)

        events = self.supabase.table("scheduled_events") \
            .select("event_type", "created_by", "created_at") \
            .in_("service_id", service_ids) \
            .gte("created_at", date_from) \
            .lte("created_at", date_to) \
            .execute().data

        total = len(events)
        ai_events = sum(1 for e in events if e["created_by"] == "AI")

        by_type: Dict[str, int] = {}
        trend: Dict[str, int] = {}

        for e in events:
            by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1
            d = e["created_at"][:10]
            trend[d] = trend.get(d, 0) + 1

        return EventMetrics(
            totale_eventi=total,
            eventi_creati_ai=ai_events,
            eventi_creati_umano=total - ai_events,
            ai_pct=round((ai_events / total * 100) if total else 0, 2),
            eventi_per_tipo=[
                EventsByTypeItem(event_type=t, count=c) for t, c in by_type.items()
            ],
            trend=[
                EventTrendItem(day=d, count=c) for d, c in trend.items()
            ],
            metadata=MetricMetadata(subscription_service_id=subscription_service_id, date_from=date_from, date_to=date_to)
        )

