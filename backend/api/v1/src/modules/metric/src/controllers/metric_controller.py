# app/controllers/metrics_controller.py
from fastapi import HTTPException, status
from typing import Optional
from src.core.DAO.metric_dao import MetricDAO
from src.modules.metric.src.utils import validate_dates, validate_subscription_id


class MetricsController:
    
    def __init__(self):
        self.metric_dao = MetricDAO()

    async def get_overview_metrics(
        self, 
        subscription_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        validate_subscription_id(subscription_id)
        try:
            df, dt = validate_dates(date_from, date_to)
            return await self.metric_dao.get_overview_metrics(subscription_id, df, dt)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Errore overview: {str(e)}"
            )

    async def get_automation_metrics(
        self, 
        subscription_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        validate_subscription_id(subscription_id)
        try:
            df, dt = validate_dates(date_from, date_to)
            return await self.metric_dao.get_automation_metrics(subscription_id, df, dt)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Errore automation: {str(e)}"
            )

    async def get_ai_quality_metrics(
        self, 
        subscription_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        validate_subscription_id(subscription_id)
        try:
            df, dt = validate_dates(date_from, date_to)
            return await self.metric_dao.get_ai_quality_metrics(subscription_id, df, dt)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Errore ai-quality: {str(e)}"
            )

    async def get_risk_metrics(
        self, 
        subscription_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        validate_subscription_id(subscription_id)
        try:
            df, dt = validate_dates(date_from, date_to)
            return await self.metric_dao.get_risk_metrics(subscription_id, df, dt)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Errore risk: {str(e)}"
            )

    async def get_usage_metrics(
        self, 
        subscription_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        validate_subscription_id(subscription_id)
        try:
            df, dt = validate_dates(date_from, date_to)
            return await self.metric_dao.get_usage_metrics(subscription_id, df, dt)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Errore usage: {str(e)}"
            )

    async def get_event_metrics(
        self, 
        subscription_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        validate_subscription_id(subscription_id)
        try:
            df, dt = validate_dates(date_from, date_to)
            return await self.metric_dao.get_event_metrics(subscription_id, df, dt)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Errore events: {str(e)}"
            )
