import json
from pydantic import BaseModel, field_validator
from google.oauth2.credentials import Credentials
from datetime import datetime
from typing import Any, Optional, List, Dict

class SubscriptionServiceCrate(BaseModel):
    subscription_id: str
    email: str
    email_provider: str
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
    microsoft_subscription_id_inbound: str | None
    microsoft_subscription_id_outbound: str | None
    microsoft_expiration_datetime_inbound: datetime | None
    microsoft_expiration_datetime_outbound: datetime | None
    oauth_user_id: str | None

    @field_validator("information", mode="before")
    @classmethod
    def _coerce_information(cls, value: Any):
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            cleaned = value.strip().translate({
                ord("\u200b"): None,  # zero-width space
                ord("\u200c"): None,
                ord("\u200d"): None,
                ord("\u2060"): None,  # word joiner
                ord("\ufeff"): None,  # BOM
            })

            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    return parsed
                return {"value": parsed}
            except Exception:
                pass

            if cleaned.lower().startswith("markdown"):
                content = cleaned[len("markdown"):].lstrip("\n\r ")
                return {"format": "markdown", "content": content}

            return {"format": "text", "content": cleaned}

        return {"value": value}

class SubscriptionServiceRead(BaseModel):
    email: str
    email_provider: Optional[str] = None
    calendar_provider: Optional[str] = None
    calendar_names: Optional[List[str]] = None
    information: Optional[Dict] = None
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    hashed_password: Optional[str] = None
    hashed_access_token: Optional[str] = None
    hashed_refresh_token: Optional[str] = None
    expiry_token: Optional[datetime] = None
    confidence_response_threshold: Optional[float] = None
    confidence_review_mail: Optional[float] = None
    priority_threshold: Optional[float] = None
    confidence_classification_threshold: Optional[float] = None
    urgent_meeting_threshold: Optional[float] = None
    history_id: Optional[str] = None
    microsoft_subscription_id_inbound: Optional[str] = None
    microsoft_subscription_id_outbound: Optional[str] = None
    microsoft_expiration_datetime_inbound: Optional[datetime] = None
    microsoft_expiration_datetime_outbound: Optional[datetime] = None
    oauth_user_id: Optional[str] = None

    @field_validator("information", mode="before")
    @classmethod
    def _coerce_information(cls, value: Any):
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            cleaned = value.strip().translate({
                ord("\u200b"): None,  # zero-width space
                ord("\u200c"): None,
                ord("\u200d"): None,
                ord("\u2060"): None,  # word joiner
                ord("\ufeff"): None,  # BOM
            })

            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    return parsed
                return {"value": parsed}
            except Exception:
                pass

            if cleaned.lower().startswith("markdown"):
                content = cleaned[len("markdown"):].lstrip("\n\r ")
                return {"format": "markdown", "content": content}

            return {"format": "text", "content": cleaned}

        return {"value": value}

class SubscriptionServiceConfigCrate(BaseModel):
    confidence_response_threshold: float | None 
    confidence_review_mail: float | None 
    priority_threshold: float | None 
    confidence_classification_threshold: float | None 
    urgent_meeting_threshold: float | None
    draft: bool | None

class OAuthGoogleCredentials(Credentials):
    def __init__(self, email: str, access_token: str, refresh_token: str, expiry: datetime, **kwargs):
        self.email = email
        super().__init__(
            token=access_token,
            refresh_token=refresh_token,
            expiry=expiry,
            **kwargs
        )

