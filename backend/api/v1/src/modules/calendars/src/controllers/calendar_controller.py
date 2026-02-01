from typing import Optional
from datetime import datetime
from src.core.DAO.calendar_dao import CalendarDAO
from src.handler_exception import InvalidFieldException, MissingFieldException
from src.modules.calendars.src.utils.utils import (
    validate_required_fields,
    parse_datetime_field,
    validate_delete_event_fields,
    validate_update_event_fields
)
    

class CalendarController:
    def __init__(self):
        self.calendar_dao = CalendarDAO()

    async def get_calendar_events(self, req: dict):
        validate_required_fields(req)
        
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
        
        time_min = parse_datetime_field(req.get("time_min"), "time_min")
        time_max = parse_datetime_field(req.get("time_max"), "time_max")
        
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

    async def create_calendar_event(self, req: dict):
        
        provider = req.get("provider", "").lower()
        email = req.get("email")
        title = req.get("title")
        description = req.get("description")
        location = req.get("location")
        attendees = req.get("attendees", [])
        is_all_day = req.get("is_all_day", False)
        calendar_id = req.get("calendar_id", "primary")
        timezone = req.get("timezone", "Europe/Rome")
        reminders = req.get("reminders")

        if provider not in ["google", "microsoft"]:
            raise InvalidFieldException(
                field="provider",
                reason="deve essere 'google' o 'microsoft'"
            )

        start = parse_datetime_field(req.get("start"), "start")
        end = parse_datetime_field(req.get("end"), "end")

        if start >= end:
            raise InvalidFieldException(
                field="start/end",
                reason="la data di inizio deve essere precedente alla data di fine"
            )

        if provider == "google":
            return await self.calendar_dao.create_google_calendar_event(
                email=email,
                title=title,
                start=start,
                end=end,
                description=description,
                location=location,
                attendees=attendees,
                is_all_day=is_all_day,
                calendar_id=calendar_id,
                timezone=timezone,
                reminders=reminders
            )
        else:
            return await self.calendar_dao.create_microsoft_calendar_event(
                email=email,
                title=title,
                start=start,
                end=end,
                description=description,
                location=location,
                attendees=attendees,
                is_all_day=is_all_day,
                calendar_id=calendar_id,
                timezone=timezone
            )

    async def update_calendar_event(self, req: dict):

        validate_update_event_fields(req)
        
        provider = req.get("provider", "").lower()
        email = req.get("email")
        event_id = req.get("event_id")
        title = req.get("title")
        description = req.get("description")
        location = req.get("location")
        attendees = req.get("attendees")
        is_all_day = req.get("is_all_day")
        calendar_id = req.get("calendar_id", "primary")
        timezone = req.get("timezone", "Europe/Rome")

        if provider not in ["google", "microsoft"]:
            raise InvalidFieldException(
                field="provider",
                reason="deve essere 'google' o 'microsoft'"
            )

        start = self._parse_datetime_field(req.get("start"), "start")
        end = self._parse_datetime_field(req.get("end"), "end")

        if start and end and start >= end:
            raise InvalidFieldException(
                field="start/end",
                reason="la data di inizio deve essere precedente alla data di fine"
            )

        if provider == "google":
            return await self.calendar_dao.update_google_calendar_event(
                email=email,
                event_id=event_id,
                title=title,
                start=start,
                end=end,
                description=description,
                location=location,
                attendees=attendees,
                is_all_day=is_all_day,
                calendar_id=calendar_id,
                timezone=timezone
            )
        else:
            return await self.calendar_dao.update_microsoft_calendar_event(
                email=email,
                event_id=event_id,
                title=title,
                start=start,
                end=end,
                description=description,
                location=location,
                attendees=attendees,
                is_all_day=is_all_day,
                calendar_id=calendar_id,
                timezone=timezone
            )

    async def delete_calendar_event(self, req: dict):
        validate_delete_event_fields(req)
        
        provider = req.get("provider", "").lower()
        email = req.get("email")
        event_id = req.get("event_id")
        calendar_id = req.get("calendar_id", "primary")

        if provider not in ["google", "microsoft"]:
            raise InvalidFieldException(
                field="provider",
                reason="deve essere 'google' o 'microsoft'"
            )

        if provider == "google":
            return await self.calendar_dao.delete_google_calendar_event(
                email=email,
                event_id=event_id,
                calendar_id=calendar_id
            )
        else:
            return await self.calendar_dao.delete_microsoft_calendar_event(
                email=email,
                event_id=event_id,
                calendar_id=calendar_id
            )
