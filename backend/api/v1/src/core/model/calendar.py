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

class CalendarEventCreateRequest(BaseModel):
    """Modello per la creazione di un evento calendario."""
    title: str 
    description: Optional[str] 
    start: datetime 
    end: datetime 
    location: Optional[str] 
    attendees: list[str] 
    is_all_day: bool 
    timezone: Optional[str] 
    reminders: Optional[list[int]] 

class CalendarEventUpdateRequest(BaseModel):
    """Modello per l'aggiornamento di un evento calendario."""
    title: Optional[str] 
    description: Optional[str]
    start: Optional[datetime]
    end: Optional[datetime]
    location: Optional[str]
    attendees: Optional[list[str]] 
    is_all_day: Optional[bool]
    timezone: Optional[str] 

class CalendarEventResponse(BaseModel):
    """Risposta per operazioni CRUD su eventi."""
    success: bool
    event_id: Optional[str] = None
    message: str
    event: Optional[CalendarEvent] = None
