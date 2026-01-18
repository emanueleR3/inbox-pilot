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
        email: str,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 100
    ) -> list[CalendarEvent]:

        token = (
            self.supabase
            .table("subscription_services")
            .select("hashed_access_token")
            .eq("email", email)
            .execute()
        )

        encrypted_token = token.get("hashed_access_token")

        decrypted_token = decrypt_token(encrypted_token, "token")
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

                events = response.json().get("items", [])
                normalized_events = [normalize_google_event(e) for e in events]

                if not normalized_events:
                    return []

                event_ids = [e.id for e in normalized_events]

                # 🔹 JOIN scheduled_events → emails
                email_bodies = {}
                try:
                    supabase_response = (
                        self.supabase
                        .table("scheduled_events")
                        .select("provider_event_id, emails(body)")
                        .in_("provider_event_id", event_ids)
                        .execute()
                    )

                    for record in supabase_response.data or []:
                        provider_event_id = record.get("provider_event_id")
                        email_data = record.get("emails")

                        if provider_event_id and email_data:
                            body = email_data.get("body")
                            if body:
                                email_bodies[provider_event_id] = body
                except Exception:
                    email_bodies = {}

                for event in normalized_events:
                    event.email_body = email_bodies.get(event.id)

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
        email: str,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 100
    ) -> list[CalendarEvent]:

        token = (
            self.supabase
            .table("subscription_services")
            .select("hashed_access_token")
            .eq("email", email)
            .execute()
        )

        encrypted_token = token.get("hashed_access_token")

        decrypted_token = decrypt_token(encrypted_token, "token")

        url = (
            "https://graph.microsoft.com/v1.0/me/calendar/events"
            if calendar_id == "primary"
            else f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events"
        )

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

                events = response.json().get("value", [])
                normalized_events = [normalize_microsoft_event(e) for e in events]

                if not normalized_events:
                    return []

                event_ids = [e.id for e in normalized_events]

                # 🔹 JOIN scheduled_events → emails
                email_bodies = {}
                try:
                    supabase_response = (
                        self.supabase
                        .table("scheduled_events")
                        .select("provider_event_id, emails(body)")
                        .in_("provider_event_id", event_ids)
                        .execute()
                    )

                    for record in supabase_response.data or []:
                        provider_event_id = record.get("provider_event_id")
                        email_data = record.get("emails")

                        if provider_event_id and email_data:
                            body = email_data.get("body")
                            if body:
                                email_bodies[provider_event_id] = body
                except Exception:
                    email_bodies = {}

                for event in normalized_events:
                    event.email_body = email_bodies.get(event.id)

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
