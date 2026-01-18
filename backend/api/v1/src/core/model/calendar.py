from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CalendarAttendee(BaseModel):
    email: str
    name: Optional[str] = None
    response_status: Optional[str] = None


class CalendarOrganizer(BaseModel):
    email: str
    name: Optional[str] = None


class CalendarEvent(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    location: Optional[str] = None
    organizer: Optional[CalendarOrganizer] = None
    attendees: list[CalendarAttendee] = Field(default_factory=list)
    is_all_day: bool = False
    status: Optional[str] = None
    html_link: Optional[str] = None
    email_body: str = "Evento non generato da email gestita da AI"


class CalendarEventsRequest(BaseModel):
    provider: str
    token: str
    time_min: Optional[datetime] = None
    time_max: Optional[datetime] = None
    max_results: Optional[int] = Field(default=100, ge=1, le=2500)
    calendar_id: Optional[str] = "primary"
