from typing import Optional, Tuple
from datetime import datetime, timedelta
from src.handler_exception import SubscriptionIdRequiredException


def validate_dates(date_from: Optional[str], date_to: Optional[str], default_days: int = 30) -> Tuple[str, str]:
    """
    Valida e normalizza le date. Se non fornite, restituisce un range di default_days giorni.
    
    Args:
        date_from: Data inizio in formato ISO
        date_to: Data fine in formato ISO
        default_days: Numero di giorni di default per il range
        
    Returns:
        Tupla (date_from, date_to) in formato ISO
    """
    if date_from and date_to:
        return date_from, date_to
    
    now = datetime.utcnow()
    return (now - timedelta(days=default_days)).isoformat(), now.isoformat()


def validate_subscription_id(subscription_id: str) -> None:
    """
    Valida che subscription_id sia presente e non vuoto.
    
    Args:
        subscription_id: ID della sottoscrizione
        
    Raises:
        SubscriptionIdRequiredException: Se subscription_id è vuoto o None
    """
    if not subscription_id:
        raise SubscriptionIdRequiredException()
