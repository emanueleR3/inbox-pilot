from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Subscription(BaseModel):
    name: str
    vat_number: Optional[str] = None
    city: str
    address: str
    active: bool = False
    current_period_end: datetime
    plan: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    products_service: Optional[str] = None
    tone_of_voice: Optional[str] = None
    phone_number: Optional[str] = None

class SubscriptionRead(BaseModel):
    subscription_id: str
    name: str
    vat_number: Optional[str] = None
    city: str
    address: str
    active: bool
    current_period_end: datetime
    plan: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    products_service: Optional[str] = None
    phone_number: Optional[str] = None

class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    vat_number: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    active: Optional[bool] = None
    current_period_end: Optional[datetime] = None
    plan: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    products_service: Optional[str] = None
    phone_number: Optional[str] = None

class SubscriptionReadWithConfig(BaseModel):
    subscription_id: str
    name: str
    vat_number: Optional[str] = None
    city: str
    address: str
    active: bool
    current_period_end: datetime
    plan: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    products_service: Optional[str] = None
    phone_number: Optional[str] = None