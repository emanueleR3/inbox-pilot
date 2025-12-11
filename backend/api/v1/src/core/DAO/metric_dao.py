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
    """
    DAO per l'accesso ai dati delle metriche.
    
    Fornisce metodi per recuperare metriche di:
    - Overview KPI
    - Automazione
    - Qualità AI
    - Rischio e alerting
    - Utilizzo e billing
    - Eventi calendario
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()

    async def normalize_dates(
        self, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ) -> Tuple[str, str]:
        """
        Normalizza le date fornite, applicando valori di default se non specificate.
        
        Args:
            date_from: Data di inizio in formato ISO (opzionale)
            date_to: Data di fine in formato ISO (opzionale)
            
        Returns:
            Tupla (date_from, date_to) con date validate o default
        """
        if date_from and date_to:
            return date_from, date_to
        now = datetime.utcnow()
        df = (now - timedelta(days=DEFAULT_DAYS)).isoformat()
        dt = now.isoformat()
        return df, dt

    async def get_overview_metrics(
        self, 
        subscription_id: str, 
        date_from: str, 
        date_to: str
    ) -> Dict[str, Any]:
        """
        Recupera le metriche di overview KPI.
        
        Args:
            subscription_id: ID della sottoscrizione
            date_from: Data di inizio in formato ISO
            date_to: Data di fine in formato ISO
            
        Returns:
            Dizionario con ticket_total, ticket_automatizzati, deflection_rate_pct,
            avg_response_time_seconds, csat_medio, alert_attivi, metadata
        """
        # Query per ticket totali
        total_result = self.supabase.rpc(
            'get_total_tickets',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        total = total_result.data if total_result.data else 0

        # Query per ticket gestiti solo da AI
        ai_result = self.supabase.rpc(
            'get_ai_only_tickets',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        ai_only = ai_result.data if ai_result.data else 0

        # Query per tempo medio di risposta
        avg_resp_result = self.supabase.rpc(
            'get_avg_response_time',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        avg_resp = avg_resp_result.data if avg_resp_result.data else 0

        # Query per CSAT medio
        csat_result = self.supabase.rpc(
            'get_avg_csat',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        csat = csat_result.data

        # Query per alert attivi
        alerts_result = self.supabase.rpc(
            'get_critical_alerts_count',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        alerts = alerts_result.data if alerts_result.data else 0

        deflection = (ai_only / total * 100) if total else 0

        return {
            "ticket_total": int(total),
            "ticket_automatizzati": int(ai_only),
            "deflection_rate_pct": float(round(deflection, 2)),
            "avg_response_time_seconds": float(round(avg_resp or 0, 2)),
            "csat_medio": (float(round(csat, 2)) if csat is not None else None),
            "alert_attivi": int(alerts),
            "metadata": {
                "date_from": date_from,
                "date_to": date_to,
                "subscription_id": subscription_id
            }
        }

    async def get_automation_metrics(
        self, 
        subscription_id: str, 
        date_from: str, 
        date_to: str
    ) -> Dict[str, Any]:
        """
        Recupera le metriche di automazione.
        
        Args:
            subscription_id: ID della sottoscrizione
            date_from: Data di inizio in formato ISO
            date_to: Data di fine in formato ISO
            
        Returns:
            Dizionario con ai_vs_human, deflection_trend, deflection_by_category,
            avg_messages_per_thread, metadata
        """
        # Query per breakdown AI vs Human
        breakdown_result = self.supabase.rpc(
            'get_ai_vs_human_breakdown',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        ai_breakdown = breakdown_result.data or []

        # Query per trend deflection
        trend_result = self.supabase.rpc(
            'get_deflection_trend',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        trend = trend_result.data or []

        # Query per deflection per categoria
        category_result = self.supabase.rpc(
            'get_deflection_by_category',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        per_cat = category_result.data or []

        # Query per media messaggi per thread
        avg_msgs_result = self.supabase.rpc(
            'get_avg_messages_per_thread',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        avg_msgs = avg_msgs_result.data if avg_msgs_result.data else 0

        return {
            "ai_vs_human": [
                {"human_response": r.get("human_response"), "count": r.get("cnt")} 
                for r in ai_breakdown
            ],
            "deflection_trend": [
                {"day": r.get("day"), "deflection_pct": float(r.get("deflection_pct") or 0)} 
                for r in trend
            ],
            "deflection_by_category": [
                {"category": r.get("category"), "deflection_pct": float(r.get("deflection_pct") or 0)} 
                for r in per_cat
            ],
            "avg_messages_per_thread": float(round(avg_msgs, 2)),
            "metadata": {"date_from": date_from, "date_to": date_to}
        }

    async def get_ai_quality_metrics(
        self, 
        subscription_id: str, 
        date_from: str, 
        date_to: str
    ) -> Dict[str, Any]:
        """
        Recupera le metriche di qualità AI.
        
        Args:
            subscription_id: ID della sottoscrizione
            date_from: Data di inizio in formato ISO
            date_to: Data di fine in formato ISO
            
        Returns:
            Dizionario con outcome_distribution, success_rate_pct, csat_distribution,
            pct_negative_feedback, avg_score_by_outcome, metadata
        """
        # Query per distribuzione outcomes
        outcomes_result = self.supabase.rpc(
            'get_outcome_distribution',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        outcomes = outcomes_result.data or []

        # Query per success rate
        success_result = self.supabase.rpc(
            'get_success_rate',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        succ = success_result.data or {"success": 0, "total": 0}

        # Query per distribuzione CSAT
        csat_result = self.supabase.rpc(
            'get_csat_distribution',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        csat_dist = csat_result.data or []

        # Query per percentuale feedback negativi
        neg_pct_result = self.supabase.rpc(
            'get_negative_feedback_pct',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        neg_pct = neg_pct_result.data if neg_pct_result.data else 0

        # Query per correlazione outcome-score
        corr_result = self.supabase.rpc(
            'get_score_by_outcome',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        corr = corr_result.data or []

        total = int(succ.get("total") or 0) if isinstance(succ, dict) else 0
        success = int(succ.get("success") or 0) if isinstance(succ, dict) else 0
        success_rate = (success / total * 100) if total else 0

        return {
            "outcome_distribution": [
                {"outcome": r.get("outcome"), "count": r.get("cnt")} 
                for r in outcomes
            ],
            "success_rate_pct": float(round(success_rate, 2)),
            "csat_distribution": [
                {"score": r.get("score"), "count": r.get("cnt")} 
                for r in csat_dist
            ],
            "pct_negative_feedback": float(round(neg_pct, 2)),
            "avg_score_by_outcome": [
                {
                    "outcome": r.get("outcome"), 
                    "avg_score": float(round(r.get("avg_score") or 0, 2)), 
                    "feedback_count": r.get("feedback_count")
                } 
                for r in corr
            ],
            "metadata": {"date_from": date_from, "date_to": date_to}
        }

    async def get_risk_metrics(
        self, 
        subscription_id: str, 
        date_from: str, 
        date_to: str
    ) -> Dict[str, Any]:
        """
        Recupera le metriche di rischio e alerting.
        
        Args:
            subscription_id: ID della sottoscrizione
            date_from: Data di inizio in formato ISO
            date_to: Data di fine in formato ISO
            
        Returns:
            Dizionario con num_ticket_critici, ticket_critici_list, priority_alerts,
            avg_time_to_first_ai_seconds, metadata
        """
        # Query per numero ticket critici
        num_crit_result = self.supabase.rpc(
            'get_critical_tickets_count',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        num_crit = num_crit_result.data if num_crit_result.data else 0

        # Query per lista ticket critici
        list_crit_result = self.supabase.rpc(
            'get_critical_tickets_list',
            {'p_subscription_id': subscription_id}
        ).execute()
        list_crit = list_crit_result.data or []

        # Query per priority alerts
        priority_result = self.supabase.rpc(
            'get_priority_alerts',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        priority_threads = priority_result.data or []

        # Query per tempo medio alla prima risposta AI
        time_first_result = self.supabase.rpc(
            'get_avg_time_to_first_ai',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        time_first = time_first_result.data if time_first_result.data else 0

        return {
            "num_ticket_critici": int(num_crit),
            "ticket_critici_list": [dict(r) for r in list_crit] if list_crit else [],
            "priority_alerts": [
                {
                    "thread_id": r.get("thread_id"), 
                    "subject": r.get("subject"), 
                    "priority_score": float(r.get("priority_score") or 0)
                } 
                for r in priority_threads
            ],
            "avg_time_to_first_ai_seconds": float(round(time_first, 2)),
            "metadata": {"date_from": date_from, "date_to": date_to}
        }

    async def get_usage_metrics(
        self, 
        subscription_id: str, 
        date_from: str, 
        date_to: str
    ) -> Dict[str, Any]:
        """
        Recupera le metriche di utilizzo e billing.
        
        Args:
            subscription_id: ID della sottoscrizione
            date_from: Data di inizio in formato ISO
            date_to: Data di fine in formato ISO
            
        Returns:
            Dizionario con email_processate, email_per_giorno, total_minutes_processed,
            thread_attivi, threads_per_category, attachments, metadata
        """
        # Query per email processate
        emails_result = self.supabase.rpc(
            'get_processed_emails_count',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        emails = emails_result.data if emails_result.data else 0

        # Query per email giornaliere
        daily_result = self.supabase.rpc(
            'get_daily_emails',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        daily = daily_result.data or []

        # Query per minuti totali
        minutes_result = self.supabase.rpc(
            'get_total_processing_minutes',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        minutes = minutes_result.data if minutes_result.data else 0

        # Query per thread attivi
        threads_active_result = self.supabase.rpc(
            'get_active_threads_count',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        threads_active = threads_active_result.data if threads_active_result.data else 0

        # Query per threads per categoria
        threads_cat_result = self.supabase.rpc(
            'get_threads_by_category',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        threads_by_cat = threads_cat_result.data or []

        # Query per statistiche allegati
        attachments_result = self.supabase.rpc(
            'get_attachment_stats',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        attachments = attachments_result.data or {}

        return {
            "email_processate": int(emails),
            "email_per_giorno": [
                {"day": r.get("day"), "count": r.get("emails_count")} 
                for r in daily
            ],
            "total_minutes_processed": float(round(minutes or 0, 2)),
            "thread_attivi": int(threads_active),
            "threads_per_category": [
                {"category": r.get("category"), "count": r.get("cnt")} 
                for r in threads_by_cat
            ],
            "attachments": attachments,
            "metadata": {"date_from": date_from, "date_to": date_to}
        }

    async def get_event_metrics(
        self, 
        subscription_id: str, 
        date_from: str, 
        date_to: str
    ) -> Dict[str, Any]:
        """
        Recupera le metriche relative agli eventi calendario.
        
        Args:
            subscription_id: ID della sottoscrizione
            date_from: Data di inizio in formato ISO
            date_to: Data di fine in formato ISO
            
        Returns:
            Dizionario con totale_eventi, eventi_creati_ai, eventi_creati_umano,
            ai_pct, eventi_per_tipo, trend, metadata
        """
        # Query per totale eventi
        total_result = self.supabase.rpc(
            'get_total_events',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        total = total_result.data if total_result.data else 0

        # Query per percentuale eventi AI
        ai_pct_result = self.supabase.rpc(
            'get_ai_events_stats',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        ai_row = ai_pct_result.data or {"ai_count": 0, "total_count": 0}

        # Query per eventi per tipo
        by_type_result = self.supabase.rpc(
            'get_events_by_type',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        by_type = by_type_result.data or []

        # Query per trend eventi
        trend_result = self.supabase.rpc(
            'get_events_trend',
            {
                'p_subscription_id': subscription_id,
                'p_date_from': date_from,
                'p_date_to': date_to
            }
        ).execute()
        trend = trend_result.data or []

        ai_count = int(ai_row.get("ai_count", 0)) if isinstance(ai_row, dict) else 0
        total_count = int(ai_row.get("total_count", 0)) if isinstance(ai_row, dict) else 0
        ai_pct = (ai_count / total_count * 100) if total_count else 0

        return {
            "totale_eventi": int(total),
            "eventi_creati_ai": ai_count,
            "eventi_creati_umano": total_count - ai_count,
            "ai_pct": float(round(ai_pct, 2)),
            "eventi_per_tipo": [
                {"event_type": r.get("event_type"), "count": r.get("cnt")} 
                for r in by_type
            ],
            "trend": [
                {"day": r.get("day"), "count": r.get("events_count")} 
                for r in trend
            ],
            "metadata": {"date_from": date_from, "date_to": date_to}
        }
