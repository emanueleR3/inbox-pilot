from typing import Optional
from datetime import datetime
from src.core.DAO.calendar_dao import CalendarDAO
from src.handler_exception import InvalidFieldException, MissingFieldException

class CalendarController:
    def __init__(self):
        self.calendar_dao = CalendarDAO()

    async def get_calendar_events(self, req: dict):
        self._validate_required_fields(req)
        
        provider = req.get("provider", "").lower()
        email = req.get("email")
        calendar_id = req.get("calendar_id", "primary")
        max_results = req.get("max_results", 100)
        
        if provider not in ["google", "microsoft"]:
            raise InvalidFieldException(
                field="provider",
                reason="deve essere 'google' o 'microsoft'"
            )
        
        if not isinstance(max_results, int) or max_results < 1 or max_results > 2500:
            raise InvalidFieldException(
                field="max_results",
                reason="deve essere un intero tra 1 e 2500"
            )
        
        time_min = self._parse_datetime_field(req.get("time_min"), "time_min")
        time_max = self._parse_datetime_field(req.get("time_max"), "time_max")
        
        if time_min and time_max and time_min >= time_max:
            raise InvalidFieldException(
                field="time_min/time_max",
                reason="time_min deve essere precedente a time_max"
            )
        
        if provider == "google":
            return await self.calendar_dao.fetch_google_calendar_events(
                email=email,
                calendar_id=calendar_id,
                time_min=time_min,
                time_max=time_max,
                max_results=max_results
            )
        else:
            return await self.calendar_dao.fetch_microsoft_calendar_events(
                email=email,
                calendar_id=calendar_id,
                time_min=time_min,
                time_max=time_max,
                max_results=max_results
            )

    def _validate_required_fields(self, request_data: dict) -> None:
        required_fields = ["provider", "email"]
        missing_fields = [field for field in required_fields if not request_data.get(field)]
        
        if missing_fields:
            raise MissingFieldException(fields=missing_fields)

    def _parse_datetime_field(self, value: Optional[str], field_name: str) -> Optional[datetime]:
        if value is None:
            return None
        
        if not isinstance(value, str):
            raise InvalidFieldException(
                field=field_name,
                reason="deve essere una stringa in formato ISO 8601"
            )
        
        try:
            if value.endswith("Z"):
                value = value.replace("Z", "+00:00")
            
            return datetime.fromisoformat(value)
        except (ValueError, AttributeError):
            raise InvalidFieldException(
                field=field_name,
                reason="formato data/ora non valido. Utilizzare formato ISO 8601 (es. 2025-01-15T10:00:00Z)"
            )
