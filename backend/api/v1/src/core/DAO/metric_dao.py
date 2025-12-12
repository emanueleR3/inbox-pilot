from typing import Any, Dict, List
from src.core.database import get_supabase_client
from src.core.DAO.model.metric import (
    Meta,
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

    def _get_service_emails(self, subscription_id: str) -> List[str]:
        services = self.supabase.table("subscription_services").select("email") \
            .eq("subscription_id", subscription_id).execute().data
        return [s["email"] for s in services]

    def _get_service_ids(self, subscription_id: str) -> List[str]:
        services = self.supabase.table("subscription_services").select("service_id") \
            .eq("subscription_id", subscription_id).execute().data
        return [s["service_id"] for s in services]

    async def get_overview_metrics(self, subscription_id: str, date_from: str, date_to: str) -> OverviewMetrics:
        service_emails = self._get_service_emails(subscription_id)

        if not service_emails:
            return OverviewMetrics(
                ticket_total=0,
                ticket_automatizzati=0,
                deflection_rate_pct=0,
                avg_response_time_seconds=0,
                alert_attivi=0,
                metadata=MetricMetadata(date_from=date_from, date_to=date_to, subscription_id=subscription_id)
            )

        threads = self.supabase.table("threads").select("thread_id", "human_response", "started_at") \
            .in_("box_email", service_emails) \
            .gte("started_at", date_from).lte("started_at", date_to).execute().data

        total = len(threads)
        ai_only = len([t for t in threads if not t["human_response"]])

        ai_emails = self.supabase.table("ai_generated_emails").select("duration", "processed_at", "service_id") \
            .gte("processed_at", date_from).lte("processed_at", date_to).execute().data

        avg_resp = (
            sum([e["duration"] for e in ai_emails]) / len(ai_emails)
            if ai_emails else 0
        )

        priority_rows = self.supabase.table("ai_generated_emails").select("priority_score") \
            .gte("processed_at", date_from).lte("processed_at", date_to).execute().data

        alerts = len([r for r in priority_rows if r["priority_score"] > 0.8])
        deflection = (ai_only / total * 100) if total > 0 else 0

        return OverviewMetrics(
            ticket_total=total,
            ticket_automatizzati=ai_only,
            deflection_rate_pct=round(deflection, 2),
            avg_response_time_seconds=round(avg_resp, 2),
            alert_attivi=alerts,
            metadata=MetricMetadata(date_from=date_from, date_to=date_to, subscription_id=subscription_id)
        )

    async def get_automation_metrics(self, subscription_id: str, date_from: str, date_to: str) -> AutomationMetrics:
        service_emails = self._get_service_emails(subscription_id)

        threads = self.supabase.table("threads").select("thread_id", "human_response", "started_at", "category") \
            .in_("box_email", service_emails) \
            .gte("started_at", date_from).lte("started_at", date_to).execute().data

        ai_vs_human = [
            AiVsHumanBreakdown(human_response=True, count=len([t for t in threads if t["human_response"]])),
            AiVsHumanBreakdown(human_response=False, count=len([t for t in threads if not t["human_response"]])),
        ]

        trend: Dict[str, Dict[str, int]] = {}
        for t in threads:
            day = t["started_at"][:10]
            if day not in trend:
                trend[day] = {"ai": 0, "total": 0}
            trend[day]["total"] += 1
            if not t["human_response"]:
                trend[day]["ai"] += 1

        deflection_trend = [
            DeflectionTrendItem(day=day, deflection_pct=(v["ai"] / v["total"] * 100 if v["total"] else 0))
            for day, v in trend.items()
        ]

        cat_map: Dict[str, Dict[str, int]] = {}
        for t in threads:
            cat = t["category"]
            if cat not in cat_map:
                cat_map[cat] = {"ai": 0, "total": 0}
            cat_map[cat]["total"] += 1
            if not t["human_response"]:
                cat_map[cat]["ai"] += 1

        deflection_by_category = [
            DeflectionByCategoryItem(category=c, deflection_pct=(v["ai"] / v["total"] * 100 if v["total"] else 0))
            for c, v in cat_map.items()
        ]

        return AutomationMetrics(
            ai_vs_human=ai_vs_human,
            deflection_trend=deflection_trend,
            deflection_by_category=deflection_by_category,
            metadata=MetricMetadata(date_from=date_from, date_to=date_to)
        )

    async def get_ai_quality_metrics(self, subscription_id: str, date_from: str, date_to: str) -> AiQualityMetrics:
        service_ids = self._get_service_ids(subscription_id)

        if not service_ids:
            return AiQualityMetrics(
                outcome_distribution=[],
                success_rate_pct=0,
                pct_negative_feedback=0,
                avg_score_by_outcome=[],
                metadata=MetricMetadata(date_from=date_from, date_to=date_to)
            )

        ai_rows = self.supabase.table("ai_generated_emails").select("outcome") \
            .in_("service_id", service_ids).gte("processed_at", date_from).lte("processed_at", date_to).execute().data

        dist: Dict[str, int] = {}
        for r in ai_rows:
            dist[r["outcome"]] = dist.get(r["outcome"], 0) + 1

        success = dist.get("success", 0)
        total = len(ai_rows)
        success_rate = (success / total * 100) if total else 0

        outcome_distribution = [
            OutcomeDistributionItem(outcome=o, count=c) for o, c in dist.items()
        ]

        return AiQualityMetrics(
            outcome_distribution=outcome_distribution,
            success_rate_pct=round(success_rate, 2),
            pct_negative_feedback=0,
            avg_score_by_outcome=[],
            metadata=MetricMetadata(date_from=date_from, date_to=date_to)
        )

    async def get_risk_metrics(self, subscription_id: str, date_from: str, date_to: str) -> RiskMetrics:
        service_ids = self._get_service_ids(subscription_id)

        ai_rows = self.supabase.table("ai_generated_emails").select("thread_id", "priority_score", "processed_at") \
            .in_("service_id", service_ids).gte("processed_at", date_from).lte("processed_at", date_to).execute().data

        priority_threads = [
            PriorityThread(
                thread_id=r["thread_id"],
                priority_score=r["priority_score"],
                processed_at=r["processed_at"]
            )
            for r in ai_rows if r["priority_score"] > 0.8
        ]

        return RiskMetrics(
            num_ticket_critici=len(priority_threads),
            ticket_critici_list=priority_threads,
            priority_alerts=priority_threads,
            avg_time_to_first_ai_seconds=0,
            metadata=MetricMetadata(date_from=date_from, date_to=date_to)
        )

    async def get_usage_metrics(self, subscription_id: str, date_from: str, date_to: str) -> UsageMetrics:
        services = self.supabase.table("subscription_services").select("service_id", "email") \
            .eq("subscription_id", subscription_id).execute().data

        service_ids = [s["service_id"] for s in services]
        emails = [s["email"] for s in services]

        emails_count = self.supabase.table("ai_generated_emails").select("email_automation_id") \
            .in_("service_id", service_ids).gte("processed_at", date_from).lte("processed_at", date_to).execute().data

        threads = self.supabase.table("threads").select("thread_id", "category", "started_at") \
            .in_("box_email", emails).gte("started_at", date_from).lte("started_at", date_to).execute().data

        threads_by_cat: Dict[str, int] = {}
        for t in threads:
            cat = t["category"]
            threads_by_cat[cat] = threads_by_cat.get(cat, 0) + 1

        attachments = self.supabase.table("email_attachments").select("size_bytes") \
            .in_("service_id", service_ids).execute().data

        total_minutes = sum([a["size_bytes"] for a in attachments]) / 60000 if attachments else 0

        threads_per_category = [
            ThreadsByCategoryItem(category=c, count=n) for c, n in threads_by_cat.items()
        ]

        return UsageMetrics(
            email_processate=len(emails_count),
            email_per_giorno=[],
            total_minutes_processed=round(total_minutes, 2),
            thread_attivi=len(threads),
            threads_per_category=threads_per_category,
            attachments=AttachmentStats(count=len(attachments)),
            metadata=MetricMetadata(date_from=date_from, date_to=date_to)
        )

    async def get_event_metrics(self, subscription_id: str, date_from: str, date_to: str) -> EventMetrics:
        service_ids = self._get_service_ids(subscription_id)

        events = self.supabase.table("scheduled_events").select("event_type", "created_by", "created_at") \
            .in_("service_id", service_ids).gte("created_at", date_from).lte("created_at", date_to).execute().data

        total = len(events)
        ai_events = len([e for e in events if e["created_by"] == "AI"])

        by_type: Dict[str, int] = {}
        for e in events:
            by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1

        trend_data: Dict[str, int] = {}
        for e in events:
            day = e["created_at"][:10]
            trend_data[day] = trend_data.get(day, 0) + 1

        eventi_per_tipo = [
            EventsByTypeItem(event_type=t, count=c) for t, c in by_type.items()
        ]

        trend = [
            EventTrendItem(day=d, count=c) for d, c in trend_data.items()
        ]

        return EventMetrics(
            totale_eventi=total,
            eventi_creati_ai=ai_events,
            eventi_creati_umano=total - ai_events,
            ai_pct=round((ai_events / total * 100) if total else 0, 2),
            eventi_per_tipo=eventi_per_tipo,
            trend=trend,
            metadata=MetricMetadata(date_from=date_from, date_to=date_to)
        )
