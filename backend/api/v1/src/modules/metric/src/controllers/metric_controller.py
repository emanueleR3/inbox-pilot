# app/controllers/metrics_controller.py
from typing import Optional
from src.core.DAO.metric_dao import MetricDAO
from src.handler_exception import SubscriptionIdRequiredException, MetricsException
from src.modules.metric.src.utils.utils import validate_dates, validate_subscription_id


class MetricsController:
    def __init__(self):
        self.metric_dao = MetricDAO()

    async def get_overview_metrics(
        self, 
        service_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        validate_subscription_id(service_id)
        try:
            df, dt = validate_dates(date_from, date_to)
            return await self.metric_dao.get_overview_metrics(service_id, df, dt)
        except SubscriptionIdRequiredException:
            raise
        except Exception as e:
            raise MetricsException(metric_type="overview", reason=str(e))

    async def get_automation_metrics(
        self, 
        service_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        validate_subscription_id(service_id)
        try:
            df, dt = validate_dates(date_from, date_to)
            return await self.metric_dao.get_automation_metrics(service_id, df, dt)
        except SubscriptionIdRequiredException:
            raise
        except Exception as e:
            raise MetricsException(metric_type="automation", reason=str(e))

    async def get_ai_quality_metrics(
        self, 
        service_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        validate_subscription_id(service_id)
        try:
            df, dt = validate_dates(date_from, date_to)
            return await self.metric_dao.get_ai_quality_metrics(service_id, df, dt)
        except SubscriptionIdRequiredException:
            raise
        except Exception as e:
            raise MetricsException(metric_type="ai-quality", reason=str(e))

    async def get_risk_metrics(
        self, 
        service_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        validate_subscription_id(service_id)
        try:
            df, dt = validate_dates(date_from, date_to)
            return await self.metric_dao.get_risk_metrics(service_id, df, dt)
        except SubscriptionIdRequiredException:
            raise
        except Exception as e:
            raise MetricsException(metric_type="risk", reason=str(e))

    async def get_usage_metrics(
        self, 
        service_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        validate_subscription_id(service_id)
        try:
            df, dt = validate_dates(date_from, date_to)
            return await self.metric_dao.get_usage_metrics(service_id, df, dt)
        except SubscriptionIdRequiredException:
            raise
        except Exception as e:
            raise MetricsException(metric_type="usage", reason=str(e))

    async def get_event_metrics(
        self, 
        service_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        validate_subscription_id(service_id)
        try:
            df, dt = validate_dates(date_from, date_to)
            return await self.metric_dao.get_event_metrics(service_id, df, dt)
        except SubscriptionIdRequiredException:
            raise
        except Exception as e:
            raise MetricsException(metric_type="events", reason=str(e))
