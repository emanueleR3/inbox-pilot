from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Subscription(BaseModel):
    name: str
    vat_number: Optional[str] = None
    city: str
    address: str
    active: bool
    current_period_end: datetime
    plan: Optional[str] = None

class SubscriptionRead(BaseModel):
    subscription_id: str
    name: str
    vat_number: Optional[str] = None
    city: str
    address: str
    active: bool
    current_period_end: datetime
    plan: Optional[str] = None