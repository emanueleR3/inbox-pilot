from pydantic import BaseModel
from datetime import datetime

class SubscriptionServiceCrate(BaseModel):
    email: str
    calendar_provider: str
    calendar_names: list[str]
    information: dict
    imap_server: str | None
    imap_port: int | None
    smtp_server: str | None
    smtp_port: int | None
    hashed_password: str | None
    hashed_access_token: str
    hashed_refresh_token: str
    expiry_token: datetime
    confidence_response_threshold: float
    confidence_review_mail: float
    priority_threshold: float
    confidence_classification_threshold: float
    urgent_meeting_threshold: float
    history_id: str
    microsoft_subscription_id: str | None
    microsoft_expiration_datetime: datetime | None
    oauth_user_id: str | None

class SubscriptionServiceRead(BaseModel):
    email: str
    calendar_provider: str
    calendar_names: list[str]
    information: dict
    imap_server: str | None
    imap_port: int | None
    smtp_server: str | None
    smtp_port: int | None
    hashed_password: str | None
    hashed_access_token: str
    hashed_refresh_token: str
    expiry_token: datetime
    confidence_response_threshold: float
    confidence_review_mail: float
    priority_threshold: float
    confidence_classification_threshold: float
    urgent_meeting_threshold: float
    history_id: str
    microsoft_subscription_id: str | None
    microsoft_expiration_datetime: datetime | None
    oauth_user_id: str | None

class SubscriptionServiceConfigCrate(BaseModel):
    confidence_response_threshold: float | None 
    confidence_review_mail: float | None 
    priority_threshold: float | None 
    confidence_classification_threshold: float | None 
    urgent_meeting_threshold: float | None 