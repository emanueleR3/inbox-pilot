from typing import Optional
from datetime import datetime, timezone
from src.handler_exception import InvalidFieldException, MissingFieldException

def validate_required_fields(request_data: dict) -> None:
    required_fields = ["provider", "email", "time_min", "time_max", "max_results"]
    missing_fields = [field for field in required_fields if not request_data.get(field)]
    
    if missing_fields:
        raise MissingFieldException(fields=missing_fields)


def parse_datetime_field(value: Optional[str], field_name: str) -> Optional[datetime]:
    if value is None:
        return None
    
    if not isinstance(value, str):
        raise InvalidFieldException(
            field=field_name,
            reason="deve essere una stringa in formato ISO 8601"
        )
    
    try:
        if value.endswith("Z"):
            value = value[:-1]  
            dt = datetime.fromisoformat(value)
            return dt.replace(tzinfo=timezone.utc)
        else:
            return datetime.fromisoformat(value)
    except (ValueError, AttributeError):
        raise InvalidFieldException(
            field=field_name,
            reason="formato data/ora non valido. Utilizzare formato ISO 8601 (es. 2025-01-15T10:00:00Z)"
        )
    
def validate_delete_event_fields(request_data: dict) -> None:
    required_fields = ["provider", "email", "event_id"]
    missing_fields = [field for field in required_fields if not request_data.get(field)]
        
    if missing_fields:
        raise MissingFieldException(fields=missing_fields)
    
def validate_update_event_fields(request_data: dict) -> None:
    required_fields = ["provider", "email", "event_id"]
    missing_fields = [field for field in required_fields if not request_data.get(field)]
        
    if missing_fields:
        raise MissingFieldException(fields=missing_fields)