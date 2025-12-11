# app/controllers/metrics_controller.py
from fastapi import HTTPException, status
from typing import Optional
from src.core.DAO.metric_DAO import MetricDAO


class MetricsController:
    """Controller per la gestione delle metriche dell'applicazione."""
    
    def __init__(self):
        self.metric_dao = MetricDAO()

    async def _validate_dates(self, date_from: Optional[str], date_to: Optional[str]):
        """Normalizza le date di input, applicando valori di default se non fornite."""
        return await self.metric_dao.normalize_dates(date_from, date_to)

    async def _validate_subscription_id(self, subscription_id: str):
        """Valida che il subscription_id sia presente."""
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
        """
        Recupera le metriche KPI overview per un abbonamento.
        
        Args:
            subscription_id: ID della sottoscrizione
            date_from: Data di inizio periodo (ISO format)
            date_to: Data di fine periodo (ISO format)
            
        Returns:
            Dizionario con le metriche di overview
            
        Raises:
            HTTPException: Se subscription_id non è valido o si verifica un errore
        """
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
        """
        Recupera le metriche di automazione per un abbonamento.
        
        Args:
            subscription_id: ID della sottoscrizione
            date_from: Data di inizio periodo (ISO format)
            date_to: Data di fine periodo (ISO format)
            
        Returns:
            Dizionario con le metriche di automazione
            
        Raises:
            HTTPException: Se subscription_id non è valido o si verifica un errore
        """
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
        """
        Recupera le metriche di qualità AI per un abbonamento.
        
        Args:
            subscription_id: ID della sottoscrizione
            date_from: Data di inizio periodo (ISO format)
            date_to: Data di fine periodo (ISO format)
            
        Returns:
            Dizionario con le metriche di qualità AI
            
        Raises:
            HTTPException: Se subscription_id non è valido o si verifica un errore
        """
        await self._validate_subscription_id(subscription_id)
        try:
            df, dt = await self._validate_dates(date_from, date_to)
            return await self.metric_dao.get_ai_quality_metrics(subscription_id, df, dt)
        exce∏pt HTTPException:
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
        """
        Recupera le metriche di rischio e alerting per un abbonamento.
        
        Args:
            subscription_id: ID della sottoscrizione
            date_from: Data di inizio periodo (ISO format)
            date_to: Data di fine periodo (ISO format)
            
        Returns:
            Dizionario con le metriche di rischio
            
        Raises:
            HTTPException: Se subscription_id non è valido o si verifica un errore
        """
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
        """
        Recupera le metriche di utilizzo e billing per un abbonamento.
        
        Args:
            subscription_id: ID della sottoscrizione
            date_from: Data di inizio periodo (ISO format)
            date_to: Data di fine periodo (ISO format)
            
        Returns:
            Dizionario con le metriche di utilizzo
            
        Raises:
            HTTPException: Se subscription_id non è valido o si verifica un errore
        """
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
        """
        Recupera le metriche relative agli eventi calendario per un abbonamento.
        
        Args:
            subscription_id: ID della sottoscrizione
            date_from: Data di inizio periodo (ISO format)
            date_to: Data di fine periodo (ISO format)
            
        Returns:
            Dizionario con le metriche degli eventi
            
        Raises:
            HTTPException: Se subscription_id non è valido o si verifica un errore
        """
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
