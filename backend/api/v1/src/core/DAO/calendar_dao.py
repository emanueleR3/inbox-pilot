import httpx
from datetime import datetime
from typing import Optional
from src.core.database import get_supabase_client
from src.core.model.calendar import CalendarEvent, CalendarAttendee, CalendarOrganizer
from src.core.utils.utils import decrypt_token, normalize_google_event, normalize_microsoft_event
from src.handler_exception import (
    GmailAPIException,
    GraphAPIException,
    InvalidTokenException
)

class CalendarDAO:
    def __init__(self):
        self.supabase = get_supabase_client()

    async def fetch_google_calendar_events(
        self,
        token: str,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 100
    ) -> list[CalendarEvent]:
        decrypted_token = decrypt_token(token, "token")
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"

        params = {
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime"
        }

        if time_min:
            params["timeMin"] = time_min.isoformat()
        if time_max:
            params["timeMax"] = time_max.isoformat()

        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params, timeout=30.0)

                if response.status_code == 401:
                    raise InvalidTokenException(provider="Google")

                if response.status_code != 200:
                    raise GmailAPIException(
                        reason=f"Status code {response.status_code}: {response.text}"
                    )

                data = response.json()
                events = data.get("items", [])

                normalized_events = [normalize_google_event(event) for event in events]

                if not normalized_events:
                    return normalized_events

                event_ids = [event.id for event in normalized_events]

                summaries = {}
                try:
                    supabase_response = (
                        self.supabase.table("scheduled_events")
                        .select("provider_event_id, threads(summary)")
                        .in_("provider_event_id", event_ids)
                        .execute()
                    )

                    for record in supabase_response.data or []:
                        provider_event_id = record.get("provider_event_id")
                        thread_data = record.get("threads")

                        if provider_event_id and thread_data:
                            summary = thread_data.get("summary")
                            if summary:
                                summaries[provider_event_id] = summary
                except Exception:
                    summaries = {}

                for event in normalized_events:
                    if event.id in summaries:
                        event.thread_summary = summaries[event.id]

                return normalized_events

        except httpx.TimeoutException:
            raise GmailAPIException(reason="Timeout durante la richiesta")
        except httpx.RequestError as e:
            raise GmailAPIException(reason=f"Errore di connessione: {str(e)}")
        except InvalidTokenException:
            raise
        except GmailAPIException:
            raise
        except Exception as e:
            raise GmailAPIException(reason=f"Errore inaspettato: {str(e)}")
        
    async def fetch_microsoft_calendar_events(
        self,
        token: str,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 100
    ) -> list[CalendarEvent]:
        decrypted_token = decrypt_token(token, "token")

        if calendar_id == "primary":
            url = "https://graph.microsoft.com/v1.0/me/calendar/events"
        else:
            url = f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events"

        params = {
            "$top": max_results,
            "$orderby": "start/dateTime"
        }

        filters = []
        if time_min:
            filters.append(f"start/dateTime ge '{time_min.isoformat()}'")
        if time_max:
            filters.append(f"end/dateTime le '{time_max.isoformat()}'")

        if filters:
            params["$filter"] = " and ".join(filters)

        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params, timeout=30.0)

                if response.status_code == 401:
                    raise InvalidTokenException(provider="Microsoft")

                if response.status_code != 200:
                    raise GraphAPIException(
                        reason=f"Status code {response.status_code}: {response.text}"
                    )

                data = response.json()
                events = data.get("value", [])

                normalized_events = [normalize_microsoft_event(event) for event in events]

                if not normalized_events:
                    return normalized_events

                event_ids = [event.id for event in normalized_events]

                summaries = {}
                try:
                    supabase_response = (
                        self.supabase.table("scheduled_events")
                        .select("provider_event_id, threads(summary)")
                        .in_("provider_event_id", event_ids)
                        .execute()
                    )

                    for record in supabase_response.data or []:
                        provider_event_id = record.get("provider_event_id")
                        thread_data = record.get("threads")

                        if provider_event_id and thread_data:
                            summary = thread_data.get("summary")
                            if summary:
                                summaries[provider_event_id] = summary
                except Exception:
                    summaries = {}

                for event in normalized_events:
                    if event.id in summaries:
                        event.thread_summary = summaries[event.id]

                return normalized_events

        except httpx.TimeoutException:
            raise GraphAPIException(reason="Timeout durante la richiesta")
        except httpx.RequestError as e:
            raise GraphAPIException(reason=f"Errore di connessione: {str(e)}")
        except InvalidTokenException:
            raise
        except GraphAPIException:
            raise
        except Exception as e:
            raise GraphAPIException(reason=f"Errore inaspettato: {str(e)}")
    
