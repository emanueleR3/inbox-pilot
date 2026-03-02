import httpx
from datetime import datetime
from typing import Optional, List
from src.core.database import get_supabase_client
from src.core.model.calendar import (
    CalendarEvent, 
    CalendarEventResponse
)
from src.core.utils.utils import decrypt_token, normalize_google_event, normalize_microsoft_event
from src.handler_exception import (
    GmailAPIException,
    GraphAPIException,
    InvalidTokenException,
    NotFoundException
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

        if not token.data:
            raise InvalidTokenException(provider="Google")

        encrypted_token = token.data[0]["hashed_access_token"]
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

        if not token.data:
            raise InvalidTokenException(provider="Google")

        encrypted_token = token.data[0]["hashed_access_token"]
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

    async def create_google_calendar_event(
        self,
        email: str,
        title: str,
        start: datetime,
        end: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        is_all_day: bool = False,
        calendar_id: str = "primary",
        timezone: str = "Europe/Rome",
        reminders: Optional[List[int]] = None
    ) -> CalendarEventResponse:
        
        token = (
            self.supabase
            .table("subscription_services")
            .select("hashed_access_token")
            .eq("email", email)
            .execute()
        )

        encrypted_token = token.data[0]["hashed_access_token"]
        decrypted_token = decrypt_token(encrypted_token, "token")

        event_payload = {
            "summary": title,
            "description": description,
            "location": location,
        }

        if is_all_day:
            event_payload["start"] = {"date": start.strftime("%Y-%m-%d")}
            event_payload["end"] = {"date": end.strftime("%Y-%m-%d")}
        else:
            event_payload["start"] = {
                "dateTime": start.isoformat(),
                "timeZone": timezone
            }
            event_payload["end"] = {
                "dateTime": end.isoformat(),
                "timeZone": timezone
            }

        if attendees:
            event_payload["attendees"] = [{"email": att} for att in attendees]

        if reminders:
            event_payload["reminders"] = {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": m} for m in reminders]
            }

        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=event_payload, timeout=30.0)

                if response.status_code == 401:
                    raise InvalidTokenException(provider="Google")

                if response.status_code not in [200, 201]:
                    raise GmailAPIException(
                        reason=f"Status code {response.status_code}: {response.text}"
                    )

                result = response.json()
                normalized_event = normalize_google_event(result)

                return CalendarEventResponse(
                    success=True,
                    event_id=result.get("id"),
                    message="Evento creato con successo",
                    event=normalized_event
                )

        except httpx.TimeoutException:
            raise GmailAPIException(reason="Timeout durante la creazione dell'evento")
        except httpx.RequestError as e:
            raise GmailAPIException(reason=f"Errore di connessione: {str(e)}")
        except InvalidTokenException:
            raise
        except GmailAPIException:
            raise
        except Exception as e:
            raise GmailAPIException(reason=f"Errore inaspettato: {str(e)}")

    async def update_google_calendar_event(
        self,
        email: str,
        event_id: str,
        title: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        is_all_day: Optional[bool] = None,
        calendar_id: str = "primary",
        timezone: str = "Europe/Rome"
    ) -> CalendarEventResponse:
        
        token = (
            self.supabase
            .table("subscription_services")
            .select("hashed_access_token")
            .eq("email", email)
            .execute()
        )

        encrypted_token = token.data[0]["hashed_access_token"]
        decrypted_token = decrypt_token(encrypted_token, "token")

        get_url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"
        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                # Recupera evento esistente
                get_response = await client.get(get_url, headers=headers, timeout=30.0)
                
                if get_response.status_code == 404:
                    raise NotFoundException(f"Evento '{event_id}' non trovato")
                if get_response.status_code == 401:
                    raise InvalidTokenException(provider="Google")
                if get_response.status_code != 200:
                    raise GmailAPIException(
                        reason=f"Status code {get_response.status_code}: {get_response.text}"
                    )

                existing_event = get_response.json()

                if title is not None:
                    existing_event["summary"] = title
                if description is not None:
                    existing_event["description"] = description
                if location is not None:
                    existing_event["location"] = location

                if start is not None and end is not None:
                    if is_all_day:
                        existing_event["start"] = {"date": start.strftime("%Y-%m-%d")}
                        existing_event["end"] = {"date": end.strftime("%Y-%m-%d")}
                    else:
                        existing_event["start"] = {
                            "dateTime": start.isoformat(),
                            "timeZone": timezone
                        }
                        existing_event["end"] = {
                            "dateTime": end.isoformat(),
                            "timeZone": timezone
                        }

                if attendees is not None:
                    existing_event["attendees"] = [{"email": att} for att in attendees]

                update_response = await client.put(
                    get_url, 
                    headers=headers, 
                    json=existing_event, 
                    timeout=30.0
                )

                if update_response.status_code == 401:
                    raise InvalidTokenException(provider="Google")
                if update_response.status_code not in [200, 201]:
                    raise GmailAPIException(
                        reason=f"Status code {update_response.status_code}: {update_response.text}"
                    )

                result = update_response.json()
                normalized_event = normalize_google_event(result)

                return CalendarEventResponse(
                    success=True,
                    event_id=result.get("id"),
                    message="Evento aggiornato con successo",
                    event=normalized_event
                )

        except httpx.TimeoutException:
            raise GmailAPIException(reason="Timeout durante l'aggiornamento dell'evento")
        except httpx.RequestError as e:
            raise GmailAPIException(reason=f"Errore di connessione: {str(e)}")
        except NotFoundException:
            raise
        except InvalidTokenException:
            raise
        except GmailAPIException:
            raise
        except Exception as e:
            raise GmailAPIException(reason=f"Errore inaspettato: {str(e)}")

    async def delete_google_calendar_event(
        self,
        email: str,
        event_id: str,
        calendar_id: str = "primary"
    ) -> CalendarEventResponse:
        """Elimina un evento da Google Calendar."""
        
        token = (
            self.supabase
            .table("subscription_services")
            .select("hashed_access_token")
            .eq("email", email)
            .execute()
        )

        encrypted_token = token.data[0]["hashed_access_token"]
        decrypted_token = decrypt_token(encrypted_token, "token")

        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"
        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=headers, timeout=30.0)

                if response.status_code == 404:
                    raise NotFoundException(f"Evento '{event_id}' non trovato")
                if response.status_code == 401:
                    raise InvalidTokenException(provider="Google")
                if response.status_code not in [200, 204]:
                    raise GmailAPIException(
                        reason=f"Status code {response.status_code}: {response.text}"
                    )

                return CalendarEventResponse(
                    success=True,
                    event_id=event_id,
                    message="Evento eliminato con successo"
                )

        except httpx.TimeoutException:
            raise GmailAPIException(reason="Timeout durante l'eliminazione dell'evento")
        except httpx.RequestError as e:
            raise GmailAPIException(reason=f"Errore di connessione: {str(e)}")
        except NotFoundException:
            raise
        except InvalidTokenException:
            raise
        except GmailAPIException:
            raise
        except Exception as e:
            raise GmailAPIException(reason=f"Errore inaspettato: {str(e)}")

    async def create_microsoft_calendar_event(
        self,
        email: str,
        title: str,
        start: datetime,
        end: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        is_all_day: bool = False,
        calendar_id: str = "primary",
        timezone: str = "Europe/Rome"
    ) -> CalendarEventResponse:
        """Crea un evento su Microsoft Calendar."""
        
        token = (
            self.supabase
            .table("subscription_services")
            .select("hashed_access_token")
            .eq("email", email)
            .execute()
        )

        encrypted_token = token.data[0]["hashed_access_token"]
        decrypted_token = decrypt_token(encrypted_token, "token")

        # Costruisci il payload per Microsoft Graph
        event_payload = {
            "subject": title,
            "body": {
                "contentType": "HTML",
                "content": description or ""
            },
            "isAllDay": is_all_day,
        }

        if is_all_day:
            event_payload["start"] = {
                "dateTime": start.strftime("%Y-%m-%dT00:00:00"),
                "timeZone": timezone
            }
            event_payload["end"] = {
                "dateTime": end.strftime("%Y-%m-%dT00:00:00"),
                "timeZone": timezone
            }
        else:
            event_payload["start"] = {
                "dateTime": start.isoformat(),
                "timeZone": timezone
            }
            event_payload["end"] = {
                "dateTime": end.isoformat(),
                "timeZone": timezone
            }

        if location:
            event_payload["location"] = {"displayName": location}

        if attendees:
            event_payload["attendees"] = [
                {
                    "emailAddress": {"address": att},
                    "type": "required"
                }
                for att in attendees
            ]

        url = (
            "https://graph.microsoft.com/v1.0/me/calendar/events"
            if calendar_id == "primary"
            else f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events"
        )
        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=event_payload, timeout=30.0)

                if response.status_code == 401:
                    raise InvalidTokenException(provider="Microsoft")

                if response.status_code not in [200, 201]:
                    raise GraphAPIException(
                        reason=f"Status code {response.status_code}: {response.text}"
                    )

                result = response.json()
                normalized_event = normalize_microsoft_event(result)

                return CalendarEventResponse(
                    success=True,
                    event_id=result.get("id"),
                    message="Evento creato con successo",
                    event=normalized_event
                )

        except httpx.TimeoutException:
            raise GraphAPIException(reason="Timeout durante la creazione dell'evento")
        except httpx.RequestError as e:
            raise GraphAPIException(reason=f"Errore di connessione: {str(e)}")
        except InvalidTokenException:
            raise
        except GraphAPIException:
            raise
        except Exception as e:
            raise GraphAPIException(reason=f"Errore inaspettato: {str(e)}")

    async def update_microsoft_calendar_event(
        self,
        email: str,
        event_id: str,
        title: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        is_all_day: Optional[bool] = None,
        calendar_id: str = "primary",
        timezone: str = "Europe/Rome"
    ) -> CalendarEventResponse:
        """Modifica un evento esistente su Microsoft Calendar."""
        
        token = (
            self.supabase
            .table("subscription_services")
            .select("hashed_access_token")
            .eq("email", email)
            .execute()
        )

        encrypted_token = token.data[0]["hashed_access_token"]
        decrypted_token = decrypt_token(encrypted_token, "token")

        url = (
            f"https://graph.microsoft.com/v1.0/me/calendar/events/{event_id}"
            if calendar_id == "primary"
            else f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events/{event_id}"
        )
        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Content-Type": "application/json"
        }

        # Costruisci payload con solo i campi da aggiornare
        update_payload = {}

        if title is not None:
            update_payload["subject"] = title
        if description is not None:
            update_payload["body"] = {
                "contentType": "HTML",
                "content": description
            }
        if location is not None:
            update_payload["location"] = {"displayName": location}
        if is_all_day is not None:
            update_payload["isAllDay"] = is_all_day

        if start is not None:
            update_payload["start"] = {
                "dateTime": start.isoformat(),
                "timeZone": timezone
            }
        if end is not None:
            update_payload["end"] = {
                "dateTime": end.isoformat(),
                "timeZone": timezone
            }

        if attendees is not None:
            update_payload["attendees"] = [
                {
                    "emailAddress": {"address": att},
                    "type": "required"
                }
                for att in attendees
            ]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(url, headers=headers, json=update_payload, timeout=30.0)

                if response.status_code == 404:
                    raise NotFoundException(f"Evento '{event_id}' non trovato")
                if response.status_code == 401:
                    raise InvalidTokenException(provider="Microsoft")
                if response.status_code != 200:
                    raise GraphAPIException(
                        reason=f"Status code {response.status_code}: {response.text}"
                    )

                result = response.json()
                normalized_event = normalize_microsoft_event(result)

                return CalendarEventResponse(
                    success=True,
                    event_id=result.get("id"),
                    message="Evento aggiornato con successo",
                    event=normalized_event
                )

        except httpx.TimeoutException:
            raise GraphAPIException(reason="Timeout durante l'aggiornamento dell'evento")
        except httpx.RequestError as e:
            raise GraphAPIException(reason=f"Errore di connessione: {str(e)}")
        except NotFoundException:
            raise
        except InvalidTokenException:
            raise
        except GraphAPIException:
            raise
        except Exception as e:
            raise GraphAPIException(reason=f"Errore inaspettato: {str(e)}")

    async def delete_microsoft_calendar_event(
        self,
        email: str,
        event_id: str,
        calendar_id: str = "primary"
    ) -> CalendarEventResponse:
        """Elimina un evento da Microsoft Calendar."""
        
        token = (
            self.supabase
            .table("subscription_services")
            .select("hashed_access_token")
            .eq("email", email)
            .execute()
        )

        encrypted_token = token.data[0]["hashed_access_token"]
        decrypted_token = decrypt_token(encrypted_token, "token")

        url = (
            f"https://graph.microsoft.com/v1.0/me/calendar/events/{event_id}"
            if calendar_id == "primary"
            else f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events/{event_id}"
        )
        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=headers, timeout=30.0)

                if response.status_code == 404:
                    raise NotFoundException(f"Evento '{event_id}' non trovato")
                if response.status_code == 401:
                    raise InvalidTokenException(provider="Microsoft")
                if response.status_code not in [200, 204]:
                    raise GraphAPIException(
                        reason=f"Status code {response.status_code}: {response.text}"
                    )

                return CalendarEventResponse(
                    success=True,
                    event_id=event_id,
                    message="Evento eliminato con successo"
                )

        except httpx.TimeoutException:
            raise GraphAPIException(reason="Timeout durante l'eliminazione dell'evento")
        except httpx.RequestError as e:
            raise GraphAPIException(reason=f"Errore di connessione: {str(e)}")
        except NotFoundException:
            raise
        except InvalidTokenException:
            raise
        except GraphAPIException:
            raise
        except Exception as e:
            raise GraphAPIException(reason=f"Errore inaspettato: {str(e)}")
