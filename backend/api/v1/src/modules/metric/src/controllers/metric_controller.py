# app/controllers/metrics_controller.py
from fastapi import HTTPException, status
from typing import Optional
from src.core.DAO.metric_DAO import MetricDAO


class MetricsController:
    
    def __init__(self):
        self.metric_dao = MetricDAO()

    async def _validate_dates(self, date_from: Optional[str], date_to: Optional[str]):
        return await self.metric_dao.normalize_dates(date_from, date_to)

    async def _validate_subscription_id(self, subscription_id: str):
        if not subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="subscription_id richiesto"
            )

    async def get_overview_metrics(
        self, 
        subscription_id: str, 
        date_from: Optional[str], 
        date_to: Optional[str]
    ):
        await self._validate_subscription_id(subscription_id)
        try:
            df, dt = await self._validate_dates(date_from, date_to)
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
        await self._validate_subscription_id(subscription_id)
        try:
            df, dt = await self._validate_dates(date_from, date_to)
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
        await self._validate_subscription_id(subscription_id)
        try:
            df, dt = await self._validate_dates(date_from, date_to)
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
        await self._validate_subscription_id(subscription_id)
        try:
            df, dt = await self._validate_dates(date_from, date_to)
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
        await self._validate_subscription_id(subscription_id)
        try:
            df, dt = await self._validate_dates(date_from, date_to)
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
        await self._validate_subscription_id(subscription_id)
        try:
            df, dt = await self._validate_dates(date_from, date_to)
            return await self.metric_dao.get_event_metrics(subscription_id, df, dt)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Errore events: {str(e)}"
            )
