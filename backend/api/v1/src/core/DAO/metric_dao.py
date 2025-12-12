# app/DAO/metric_DAO.py
"""
Data Access Object per le metriche dell'applicazione.
Gestisce tutte le query al database per recuperare le diverse tipologie di metriche.
"""
from typing import Optional, Tuple, Any, Dict, List
from datetime import datetime, timedelta
from src.core.database import get_supabase_client

DEFAULT_DAYS = 30


class MetricDAO:

    def __init__(self):
        self.supabase = get_supabase_client()

    # ---------------------------------------------------------
    # NORMALIZZAZIONE DATE
    # ---------------------------------------------------------
    async def normalize_dates(self, date_from: Optional[str], date_to: Optional[str]) -> Tuple[str, str]:
        if date_from and date_to:
            return date_from, date_to
        
        now = datetime.utcnow()
        return (now - timedelta(days=DEFAULT_DAYS)).isoformat(), now.isoformat()

    # ---------------------------------------------------------
    # METRICHE OVERVIEW
    # ---------------------------------------------------------
    async def get_overview_metrics(self, subscription_id: str, date_from: str, date_to: str) -> Dict[str, Any]:

        # Recupero tutte le caselle email di questa subscription
        services = self.supabase.table("subscription_services").select("email") \
            .eq("subscription_id", subscription_id).execute().data

        service_emails = [s["email"] for s in services]

        if not service_emails:
            return {
                "ticket_total": 0,
                "ticket_automatizzati": 0,
                "deflection_rate_pct": 0,
                "avg_response_time_seconds": 0,
                "csat_medio": None,
                "alert_attivi": 0,
                "metadata": {"date_from": date_from, "date_to": date_to}
            }

        # THREAD TOTALI
        threads = self.supabase.table("threads").select("thread_id", "human_response", "started_at") \
            .in_("box_email", service_emails) \
            .gte("started_at", date_from).lte("started_at", date_to).execute().data

        total = len(threads)

        # AI-only ticket = quelli con human_response = false
        ai_only = len([t for t in threads if not t["human_response"]])

        # calcolo risposta media dell'AI usando ai_generated_emails
        ai_emails = self.supabase.table("ai_generated_emails").select("duration", "processed_at", "service_id") \
            .gte("processed_at", date_from).lte("processed_at", date_to).execute().data

        avg_resp = (
            sum([e["duration"] for e in ai_emails]) / len(ai_emails)
            if ai_emails else 0
        )

        # CSAT medio da human_feedback
        csat_rows = self.supabase.table("human_feedback").select("score") \
            .gte("created_at", date_from).lte("created_at", date_to).execute().data

        csat = (sum([r["score"] for r in csat_rows]) / len(csat_rows)) if csat_rows else None

        # Alert critici = priority_score > threshold (non esiste colonna alerts, useremo ai_generated_emails)
        priority_rows = self.supabase.table("ai_generated_emails").select("priority_score") \
            .gte("processed_at", date_from).lte("processed_at", date_to).execute().data

        alerts = len([r for r in priority_rows if r["priority_score"] > 0.8])  # soglia arbitraria

        deflection = (ai_only / total * 100) if total > 0 else 0

        return {
            "ticket_total": total,
            "ticket_automatizzati": ai_only,
            "deflection_rate_pct": round(deflection, 2),
            "avg_response_time_seconds": round(avg_resp, 2),
            "csat_medio": round(csat, 2) if csat is not None else None,
            "alert_attivi": alerts,
            "metadata": {"date_from": date_from, "date_to": date_to, "subscription_id": subscription_id}
        }

    # ---------------------------------------------------------
    # METRICHE AUTOMAZIONE
    # ---------------------------------------------------------
    async def get_automation_metrics(self, subscription_id: str, date_from: str, date_to: str) -> Dict[str, Any]:

        services = self.supabase.table("subscription_services").select("email") \
            .eq("subscription_id", subscription_id).execute().data
        service_emails = [s["email"] for s in services]

        threads = self.supabase.table("threads").select("thread_id", "human_response", "started_at", "category") \
            .in_("box_email", service_emails) \
            .gte("started_at", date_from).lte("started_at", date_to).execute().data

        # Breakdown AI vs Human
        ai_vs_human = [
            {"human_response": True, "count": len([t for t in threads if t["human_response"]])},
            {"human_response": False, "count": len([t for t in threads if not t["human_response"]])},
        ]

        # Trend giornaliero deflection
        trend = {}
        for t in threads:
            day = t["started_at"][:10]
            if day not in trend:
                trend[day] = {"ai": 0, "total": 0}
            trend[day]["total"] += 1
            if not t["human_response"]:
                trend[day]["ai"] += 1

        deflection_trend = [
            {"day": day, "deflection_pct": (v["ai"] / v["total"] * 100 if v["total"] else 0)}
            for day, v in trend.items()
        ]

        # Deflection per categoria
        cat_map = {}
        for t in threads:
            cat = t["category"]
            if cat not in cat_map:
                cat_map[cat] = {"ai": 0, "total": 0}
            cat_map[cat]["total"] += 1
            if not t["human_response"]:
                cat_map[cat]["ai"] += 1

        deflection_by_category = [
            {"category": c, "deflection_pct": (v["ai"] / v["total"] * 100 if v["total"] else 0)}
            for c, v in cat_map.items()
        ]

        # Media messaggi per thread = length(history)
        avg_messages = (
            sum([len(t["history"]) for t in threads]) / len(threads)
            if threads else 0
        )

        return {
            "ai_vs_human": ai_vs_human,
            "deflection_trend": deflection_trend,
            "deflection_by_category": deflection_by_category,
            "avg_messages_per_thread": round(avg_messages, 2),
            "metadata": {"date_from": date_from, "date_to": date_to}
        }

    # ---------------------------------------------------------
    # METRICHE QUALITÀ AI
    # ---------------------------------------------------------
    async def get_ai_quality_metrics(self, subscription_id: str, date_from: str, date_to: str) -> Dict[str, Any]:

        # Recupero service_id
        services = self.supabase.table("subscription_services").select("service_id").eq("subscription_id", subscription_id).execute().data
        service_ids = [s["service_id"] for s in services]

        if not service_ids:
            return {
                "outcome_distribution": [],
                "success_rate_pct": 0,
                "csat_distribution": [],
                "pct_negative_feedback": 0,
                "avg_score_by_outcome": [],
                "metadata": {"date_from": date_from, "date_to": date_to}
            }

        # outcome distribuiton
        ai_rows = self.supabase.table("ai_generated_emails").select("outcome") \
            .in_("service_id", service_ids).gte("processed_at", date_from).lte("processed_at", date_to).execute().data

        dist = {}
        for r in ai_rows:
            dist[r["outcome"]] = dist.get(r["outcome"], 0) + 1

        # success rate
        success = dist.get("success", 0)
        total = len(ai_rows)
        success_rate = (success / total * 100) if total else 0

        # csat distribution
        fb = self.supabase.table("human_feedback").select("score").execute().data
        fb_dist = {}
        for f in fb:
            score = int(f["score"])
            fb_dist[score] = fb_dist.get(score, 0) + 1

        # negative feedback pct
        neg = fb_dist.get(1, 0) + fb_dist.get(2, 0)
        pct_neg = (neg / sum(fb_dist.values()) * 100) if fb_dist else 0

        return {
            "outcome_distribution": [{"outcome": o, "count": c} for o, c in dist.items()],
            "success_rate_pct": round(success_rate, 2),
            "csat_distribution": [{"score": s, "count": c} for s, c in fb_dist.items()],
            "pct_negative_feedback": round(pct_neg, 2),
            "avg_score_by_outcome": [],  # non esiste collegamento outcome → feedback nel tuo schema
            "metadata": {"date_from": date_from, "date_to": date_to}
        }

    # ---------------------------------------------------------
    # METRICHE RISCHIO
    # ---------------------------------------------------------
    async def get_risk_metrics(self, subscription_id: str, date_from: str, date_to: str) -> Dict[str, Any]:

        # critical ticket = threads con priority_score alto in ai_generated_emails
        services = self.supabase.table("subscription_services").select("service_id", "email") \
            .eq("subscription_id", subscription_id).execute().data

        service_ids = [s["service_id"] for s in services]
        emails = [s["email"] for s in services]

        ai_rows = self.supabase.table("ai_generated_emails").select("thread_id", "priority_score", "processed_at") \
            .in_("service_id", service_ids).gte("processed_at", date_from).lte("processed_at", date_to).execute().data

        priority_threads = [r for r in ai_rows if r["priority_score"] > 0.8]

        return {
            "num_ticket_critici": len(priority_threads),
            "ticket_critici_list": priority_threads,
            "priority_alerts": priority_threads,
            "avg_time_to_first_ai_seconds": 0,  # non hai timestamp necessario
            "metadata": {"date_from": date_from, "date_to": date_to}
        }

    # ---------------------------------------------------------
    # METRICHE UTILIZZO
    # ---------------------------------------------------------
    async def get_usage_metrics(self, subscription_id: str, date_from: str, date_to: str) -> Dict[str, Any]:

        services = self.supabase.table("subscription_services").select("service_id", "email") \
            .eq("subscription_id", subscription_id).execute().data

        service_ids = [s["service_id"] for s in services]
        emails = [s["email"] for s in services]

        # email processate = ai_generated_emails + threads?
        emails_count = self.supabase.table("ai_generated_emails").select("email_automation_id") \
            .in_("service_id", service_ids).gte("processed_at", date_from).lte("processed_at", date_to).execute().data

        # threads attivi
        threads = self.supabase.table("threads").select("thread_id", "category", "started_at") \
            .in_("box_email", emails).gte("started_at", date_from).lte("started_at", date_to).execute().data

        threads_by_cat = {}
        for t in threads:
            cat = t["category"]
            threads_by_cat[cat] = threads_by_cat.get(cat, 0) + 1

        # attachment stats
        attachments = self.supabase.table("email_attachments").select("size_bytes") \
            .in_("service_id", service_ids).execute().data

        total_minutes = sum([a["size_bytes"] for a in attachments]) / 60000 if attachments else 0

        return {
            "email_processate": len(emails_count),
            "email_per_giorno": [],  # optional da ricostruire
            "total_minutes_processed": round(total_minutes, 2),
            "thread_attivi": len(threads),
            "threads_per_category": [{"category": c, "count": n} for c, n in threads_by_cat.items()],
            "attachments": {"count": len(attachments)},
            "metadata": {"date_from": date_from, "date_to": date_to}
        }

    # ---------------------------------------------------------
    # METRICHE EVENTI
    # ---------------------------------------------------------
    async def get_event_metrics(self, subscription_id: str, date_from: str, date_to: str) -> Dict[str, Any]:

        services = self.supabase.table("subscription_services").select("service_id") \
            .eq("subscription_id", subscription_id).execute().data

        service_ids = [s["service_id"] for s in services]

        events = self.supabase.table("scheduled_events").select("event_type", "created_by", "created_at") \
            .in_("service_id", service_ids).gte("created_at", date_from).lte("created_at", date_to).execute().data

        total = len(events)
        ai_events = len([e for e in events if e["created_by"] == "AI"])

        by_type = {}
        for e in events:
            by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1

        trend = {}
        for e in events:
            day = e["created_at"][:10]
            trend[day] = trend.get(day, 0) + 1

        return {
            "totale_eventi": total,
            "eventi_creati_ai": ai_events,
            "eventi_creati_umano": total - ai_events,
            "ai_pct": round((ai_events / total * 100) if total else 0, 2),
            "eventi_per_tipo": [{"event_type": t, "count": c} for t, c in by_type.items()],
            "trend": [{"day": d, "count": c} for d, c in trend.items()],
            "metadata": {"date_from": date_from, "date_to": date_to}
        }
