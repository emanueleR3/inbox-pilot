import os
import base64
import hashlib
from cryptography.fernet import Fernet

from datetime import datetime, timedelta, timezone
from typing import List, Optional
import httpx
from zoneinfo import ZoneInfo

# Mapping of European countries to their timezones
COUNTRY_TIMEZONE_MAP = {
    "Italy": "Europe/Rome",
    "United Kingdom": "Europe/London",
    "Germany": "Europe/Berlin",
    "France": "Europe/Paris",
    "Spain": "Europe/Madrid",
    "Portugal": "Europe/Lisbon",
    "Netherlands": "Europe/Amsterdam",
    "Belgium": "Europe/Brussels",
    "Austria": "Europe/Vienna",
    "Switzerland": "Europe/Zurich",
    "Greece": "Europe/Athens",
    "Poland": "Europe/Warsaw",
    "Czech Republic": "Europe/Prague",
    "Hungary": "Europe/Budapest",
    "Romania": "Europe/Bucharest",
    "Sweden": "Europe/Stockholm",
    "Norway": "Europe/Oslo",
    "Denmark": "Europe/Copenhagen",
    "Finland": "Europe/Helsinki",
    "Ireland": "Europe/Dublin",
    "Croatia": "Europe/Zagreb",
    "Bulgaria": "Europe/Sofia",
    "Slovakia": "Europe/Bratislava",
    "Slovenia": "Europe/Ljubljana",
    "Lithuania": "Europe/Vilnius",
    "Latvia": "Europe/Riga",
    "Estonia": "Europe/Tallinn",
    "Luxembourg": "Europe/Luxembourg",
    "Malta": "Europe/Malta",
    "Cyprus": "Asia/Nicosia",
    "Iceland": "Atlantic/Reykjavik",
}

def get_timezone_from_country(country: str) -> str:
    """
    Get timezone string from country name.
    
    Args:
        country: Country name (e.g., "Italy", "Germany")
        
    Returns:
        Timezone string (e.g., "Europe/Rome"). Defaults to "Europe/Rome" if country not found.
    """
    timezone = COUNTRY_TIMEZONE_MAP.get(country)
    if not timezone:
        print(f"⚠️ Country '{country}' not found in timezone map, using default Europe/Rome")
        return "Europe/Rome"
    return timezone


def get_google_calendar_timezone(token: str) -> str:
    """
    Retrieve timezone from Google Calendar user settings.
    
    Args:
        token: Google access token
        
    Returns:
        Timezone string (e.g., "Europe/Rome"). Defaults to "Europe/Rome" on error.
    """
    url = "https://www.googleapis.com/calendar/v3/users/me/settings/timezone"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        timezone = data.get("value", "Europe/Rome")
        print(f"🌍 Retrieved Google Calendar timezone: {timezone}")
        return timezone
    except Exception as e:
        print(f"❌ Error retrieving Google Calendar timezone: {e}")
        print(f"   Using default: Europe/Rome")
        return "Europe/Rome"


# Mapping of Microsoft timezone names to IANA timezone strings
MICROSOFT_TIMEZONE_MAP = {
    "W. Europe Standard Time": "Europe/Rome",
    "GMT Standard Time": "Europe/London",
    "Romance Standard Time": "Europe/Paris",
    "Central Europe Standard Time": "Europe/Warsaw",
    "Central European Standard Time": "Europe/Belgrade",
    "E. Europe Standard Time": "Europe/Bucharest",
    "FLE Standard Time": "Europe/Helsinki",
    "GTB Standard Time": "Europe/Athens",
    "UTC": "UTC",
    "Eastern Standard Time": "America/New_York",
    "Central Standard Time": "America/Chicago",
    "Mountain Standard Time": "America/Denver",
    "Pacific Standard Time": "America/Los_Angeles",
}


def get_microsoft_calendar_timezone(token: str) -> str:
    """
    Retrieve timezone from Microsoft Calendar settings.
    
    Tries multiple endpoints in order of preference:
    1. Default calendar settings (requires Calendars.Read/ReadWrite)
    2. Recent calendar events (requires Calendars.Read/ReadWrite)
    3. Mailbox settings (requires MailboxSettings.Read)
    4. Default to Europe/Rome
    
    Args:
        token: Microsoft access token
        
    Returns:
        Timezone string in IANA format (e.g., "Europe/Rome"). Defaults to "Europe/Rome" on error.
    """
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Method 1: Get timezone directly from the user's default calendar
    # The calendar object has a "timeZone" property (requires Calendars.Read or Calendars.ReadWrite)
    try:
        # Request the calendar with specific properties including timeZone
        calendar_url = "https://graph.microsoft.com/v1.0/me/calendar?$select=id,name,timeZone"
        response = httpx.get(calendar_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # The calendar object contains the timeZone property
        ms_timezone = data.get("timeZone")
        if ms_timezone:
            print(f"🌍 Retrieved Microsoft timezone from calendar: {ms_timezone}")
            
            # Convert Microsoft timezone to IANA format
            iana_timezone = MICROSOFT_TIMEZONE_MAP.get(ms_timezone, ms_timezone)
            
            # If it's already IANA format (contains /), use it directly
            if "/" in ms_timezone:
                iana_timezone = ms_timezone
            elif ms_timezone not in MICROSOFT_TIMEZONE_MAP:
                print(f"⚠️ Microsoft timezone '{ms_timezone}' not in mapping, using as-is or default")
                iana_timezone = "Europe/Rome"
            
            print(f"   Converted to IANA: {iana_timezone}")
            return iana_timezone
    except Exception as e:
        print(f"⚠️ Could not get timezone from calendar: {e}")
    
    # Method 2: Try to infer timezone from a recent calendar event
    try:
        events_url = "https://graph.microsoft.com/v1.0/me/calendar/events"
        params = {
            "$top": "1",
            "$orderby": "createdDateTime desc",
            "$select": "start,end"
        }
        response = httpx.get(events_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        events = data.get("value", [])
        
        if events:
            event = events[0]
            # Get timezone from event start
            event_tz = event.get("start", {}).get("timeZone")
            if event_tz:
                print(f"🌍 Inferred Microsoft timezone from recent event: {event_tz}")
                iana_timezone = MICROSOFT_TIMEZONE_MAP.get(event_tz, event_tz)
                # If it's already IANA format, use it directly
                if "/" in event_tz:
                    iana_timezone = event_tz
                print(f"   Timezone: {iana_timezone}")
                return iana_timezone
        else:
            print(f"⚠️ No calendar events found to infer timezone")
    except Exception as e:
        print(f"⚠️ Could not infer timezone from events: {e}")
    
    # Method 3: Try mailbox settings as last resort (requires MailboxSettings.Read permission)
    try:
        mailbox_url = "https://graph.microsoft.com/v1.0/me/mailboxSettings"
        response = httpx.get(mailbox_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        ms_timezone = data.get("timeZone", "W. Europe Standard Time")
        print(f"🌍 Retrieved Microsoft timezone from mailboxSettings: {ms_timezone}")
        
        # Convert Microsoft timezone to IANA format
        iana_timezone = MICROSOFT_TIMEZONE_MAP.get(ms_timezone, "Europe/Rome")
        if ms_timezone not in MICROSOFT_TIMEZONE_MAP:
            print(f"⚠️ Microsoft timezone '{ms_timezone}' not in mapping, using default Europe/Rome")
        
        print(f"   Converted to IANA: {iana_timezone}")
        return iana_timezone
    except Exception as e:
        print(f"⚠️ Could not get mailboxSettings (likely missing MailboxSettings.Read permission): {e}")
    
    # Fallback to default
    print(f"⚠️ Could not determine Microsoft timezone, using default: Europe/Rome")
    return "Europe/Rome"

encryption_key_token = os.getenv("ENCRYPTION_KEY_TOKEN")
encryption_key_pass = os.getenv("ENCRYPTION_KEY_PASS")

if not encryption_key_token:
    raise ValueError("ENCRYPTION_KEY_TOKEN non trovata nelle variabili d'ambiente")
if not encryption_key_pass:
    raise ValueError("ENCRYPTION_KEY_PASS non trovata nelle variabili d'ambiente")

_key_token = encryption_key_token.encode()
_hash_token = hashlib.sha256(_key_token).digest()
_cipher_token = Fernet(base64.urlsafe_b64encode(_hash_token))
_key_pass = encryption_key_pass.encode()
_hash_pass = hashlib.sha256(_key_pass).digest()
_cipher_pass = Fernet(base64.urlsafe_b64encode(_hash_pass))

def decrypt(value: str, cond: str) -> str:
    if not value:
        return ""

    if cond == "token":
        cipher = _cipher_token
    elif cond == "pass":
        cipher = _cipher_pass
    else:
        raise ValueError("cond deve essere 'token' o 'pass'")

    return cipher.decrypt(value.encode()).decode()

def get_google_busy_slots(token: str, start_time: datetime, end_time: datetime) -> List[tuple]:
    """
    Get busy time slots from Google Calendar with event IDs.
    
    Returns:
        List of tuples: (start_datetime, end_datetime, event_id)
    """
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Ensure times are in UTC for API request
    if start_time.tzinfo is None:
        start_time_utc = start_time.replace(tzinfo=timezone.utc)
    else:
        start_time_utc = start_time.astimezone(timezone.utc)
    
    if end_time.tzinfo is None:
        end_time_utc = end_time.replace(tzinfo=timezone.utc)
    else:
        end_time_utc = end_time.astimezone(timezone.utc)
    
    params = {
        "timeMin": start_time_utc.isoformat(),
        "timeMax": end_time_utc.isoformat(),
        "singleEvents": True,
        "orderBy": "startTime"
    }
    
    try:
        response = httpx.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        events = data.get("items", [])
        slots = []
        for event in events:
            # Skip all-day events
            if "dateTime" not in event.get("start", {}):
                continue
            
            start = datetime.fromisoformat(event["start"]["dateTime"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(event["end"]["dateTime"].replace("Z", "+00:00"))
            event_id = event.get("id")
            slots.append((start, end, event_id))
        return slots
    except Exception as e:
        print(f"Error fetching Google calendar events: {e}")
        return []

def get_microsoft_busy_slots(token: str, start_time: datetime, end_time: datetime) -> List[tuple]:
    """
    Get busy time slots from Microsoft Calendar with event IDs.
    
    Returns:
        List of tuples: (start_datetime, end_datetime, event_id)
    """
    url = "https://graph.microsoft.com/v1.0/me/calendar/calendarView"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Ensure times are in UTC for API request
    if start_time.tzinfo is None:
        start_time_utc = start_time.replace(tzinfo=timezone.utc)
    else:
        start_time_utc = start_time.astimezone(timezone.utc)
    
    if end_time.tzinfo is None:
        end_time_utc = end_time.replace(tzinfo=timezone.utc)
    else:
        end_time_utc = end_time.astimezone(timezone.utc)
    
    params = {
        "startDateTime": start_time_utc.isoformat(),
        "endDateTime": end_time_utc.isoformat()
    }
    
    try:
        response = httpx.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        events = data.get("value", [])
        slots = []
        for event in events:
            # Skip all-day events
            if not event.get("start", {}).get("dateTime"):
                continue
            
            start = datetime.fromisoformat(event["start"]["dateTime"])
            end = datetime.fromisoformat(event["end"]["dateTime"])
            event_id = event.get("id")
            slots.append((start, end, event_id))
        return slots
    except Exception as e:
        print(f"Error fetching Microsoft calendar events: {e}")
        return []

def calculate_free_slots(
    start_time: datetime, 
    end_time: datetime, 
    busy_slots: List[tuple], 
    business_hours: dict, 
    duration: int,
    not_available_dates: Optional[List[str]],
    user_timezone: str = "Europe/Rome"  # Default timezone for Italy
) -> List[str]:
    """
    Calculate free slots based on business hours.
    
    Args:
        start_time: Start of search period
        end_time: End of search period
        busy_slots: List of (start, end) busy time tuples
        business_hours: Dict with weekday as key (0=Monday, 6=Sunday) and list of time ranges as value
                       Example: {"0": ["9:00-13:00", "15:00-18:00"], "1": ["9:00-13:00"]}
        duration: Appointment duration in minutes
        not_available_dates: List of dates to exclude (format: YYYY-MM-DD)
        user_timezone: Timezone string (e.g., "Europe/Rome")
        
    Returns:
        List of available time slots in ISO format
    """
    
    print("\n====== DEBUG calculate_free_slots() START ======")
    print(f"start_time: {start_time}")
    print(f"end_time:   {end_time}")
    print(f"business_hours: {business_hours}")
    print(f"duration: {duration}")
    print(f"busy_slots: {len(busy_slots)} items")
    print(f"not_available_dates: {not_available_dates}")
    print(f"user_timezone: {user_timezone}")
    print("================================================\n")

    # Convert business_hours keys to set of working weekdays
    working_days = {int(day) for day in business_hours.keys()}
    
    # Get user timezone
    tz = ZoneInfo(user_timezone)
    
    # Convert start_time and end_time to user timezone if they are naive
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=tz)
    else:
        start_time = start_time.astimezone(tz)
    
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=tz)
    else:
        end_time = end_time.astimezone(tz)

    free_slots = []
    
    # Round to next slot boundary based on duration
    # Slots must start at "round" times: for 60min -> start of hour, for 30min -> :00 or :30, for 15min -> :00, :15, :30, :45
    current_time = start_time
    
    # Calculate next round time based on duration
    if duration >= 60:
        # For 60+ minutes: round to next hour
        if current_time.minute > 0 or current_time.second > 0 or current_time.microsecond > 0:
            current_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    elif duration >= 30:
        # For 30-59 minutes: round to next half hour (:00 or :30)
        if current_time.minute < 30:
            current_time = current_time.replace(minute=30, second=0, microsecond=0)
        else:
            current_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    elif duration >= 15:
        # For 15-29 minutes: round to next quarter hour (:00, :15, :30, :45)
        next_quarter = ((current_time.minute // 15) + 1) * 15
        if next_quarter >= 60:
            current_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            current_time = current_time.replace(minute=next_quarter, second=0, microsecond=0)
    else:
        # For < 15 minutes: round to next 15 minutes
        next_quarter = ((current_time.minute // 15) + 1) * 15
        if next_quarter >= 60:
            current_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            current_time = current_time.replace(minute=next_quarter, second=0, microsecond=0)
    
    print(f"🔄 Rounded start_time to next slot boundary: {current_time}")

    # Normalize not_available_dates
    not_avail_set = set(not_available_dates or [])

    while current_time + timedelta(minutes=duration) <= end_time:

        print(f"\n[ITER] Checking: {current_time}")
        
        weekday = current_time.weekday()
        weekday_str = str(weekday)

        # Not working day
        if weekday_str not in business_hours:
            print(f"  ⛔ Skipped: not working day (weekday={weekday})")
            current_time += timedelta(days=1)
            current_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            continue
        
        # Day rejected
        if current_time.strftime("%Y-%m-%d") in not_avail_set:
            print(f"  ⛔ Skipped: date rejected ({current_time.strftime('%Y-%m-%d')})")
            current_time += timedelta(days=1)
            current_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            continue
        
        # Get business hours for this weekday
        day_hours = business_hours[weekday_str]  # e.g., ["9:00-13:00", "15:00-18:00"]
        
        # Check if current_time falls within any of the business hour ranges
        slot_end = current_time + timedelta(minutes=duration)
        is_within_hours = False
        next_opening = None
        
        for time_range in day_hours:
            try:
                open_str, close_str = time_range.split("-")
                open_h, open_m = map(int, open_str.split(":"))
                close_h, close_m = map(int, close_str.split(":"))
                
                range_open = current_time.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
                range_close = current_time.replace(hour=close_h, minute=close_m, second=0, microsecond=0)
                
                # Check if slot fits within this range
                if current_time >= range_open and slot_end <= range_close:
                    is_within_hours = True
                    break
                
                # Track next opening time if we're before it
                if current_time < range_open and (next_opening is None or range_open < next_opening):
                    next_opening = range_open
                    
            except ValueError:
                print(f"  ⚠️ Invalid time range format: {time_range}")
                continue
        
        # If not within any business hours, jump to next opening or next day
        if not is_within_hours:
            if next_opening and next_opening > current_time:
                print(f"  ⛔ Outside business hours, jumping to next opening: {next_opening}")
                current_time = next_opening
                continue
            else:
                print(f"  ⛔ No more openings today, moving to next day")
                current_time += timedelta(days=1)
                current_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                continue

        # Busy slot overlap - convert busy slots to user timezone for comparison
        is_busy = False
        for busy_slot in busy_slots:
            # Handle both 2-tuple (old format) and 3-tuple (new format with event_id)
            if len(busy_slot) == 3:
                b_start, b_end, b_event_id = busy_slot
            else:
                b_start, b_end = busy_slot
                b_event_id = None
            
            # Convert busy slot times to user timezone
            if b_start.tzinfo is not None:
                b_start_local = b_start.astimezone(tz)
            else:
                b_start_local = b_start.replace(tzinfo=tz)
            
            if b_end.tzinfo is not None:
                b_end_local = b_end.astimezone(tz)
            else:
                b_end_local = b_end.replace(tzinfo=tz)
            
            if current_time < b_end_local and slot_end > b_start_local:
                print(f"  ⛔ Overlaps busy: {b_start_local} -> {b_end_local}")
                is_busy = True
                break

        if not is_busy:
            print(f"  ✅ FREE SLOT: {current_time.isoformat()}")
            free_slots.append(current_time.isoformat())
            if len(free_slots) >= 3:
                print("=== RETURNING FIRST 3 FREE SLOTS ===")
                return free_slots
            
            # Move to next slot boundary based on duration
            if duration >= 60:
                # For 60+ minutes: move to next hour
                current_time += timedelta(hours=1)
            elif duration >= 30:
                # For 30-59 minutes: move to next half hour
                current_time += timedelta(minutes=30)
            elif duration >= 15:
                # For 15-29 minutes: move to next quarter hour
                current_time += timedelta(minutes=15)
            else:
                # For < 15 minutes: move to next 15 minutes
                current_time += timedelta(minutes=15)
        else:
            # Move forward by slot increment to check next boundary
            if duration >= 60:
                current_time += timedelta(hours=1)
            elif duration >= 30:
                current_time += timedelta(minutes=30)
            elif duration >= 15:
                current_time += timedelta(minutes=15)
            else:
                current_time += timedelta(minutes=15)

    print("=== END — Returning free_slots ===")
    return free_slots


def create_google_calendar_event(
    token: str, 
    title: str, 
    start_time: datetime, 
    end_time: datetime,
    attendees: Optional[List[str]] = None,
    location: Optional[str] = None,
    description: Optional[str] = None
) -> Optional[str]:
    """Create a Google Calendar event with full details."""
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Ensure datetime has timezone info - if not, assume UTC
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    
    # Google expects RFC3339 format with timezone
    body = {
        "summary": title,
        "start": {
            "dateTime": start_time.isoformat()
        },
        "end": {
            "dateTime": end_time.isoformat()
        }
    }
    
    # Add optional fields
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    if attendees:
        body["attendees"] = [{"email": email} for email in attendees]
    
    try:
        response = httpx.post(url, headers=headers, json=body)
        response.raise_for_status()
        event_data = response.json()
        event_id = event_data.get("id")
        print(f"✅ Created Google calendar event with ID: {event_id}")
        return event_id  # Return the Google event ID
    except Exception as e:
        print(f"Error creating Google calendar event: {e}")
        return None

def create_microsoft_calendar_event(
    token: str, 
    title: str, 
    start_time: datetime, 
    end_time: datetime,
    attendees: Optional[List[str]] = None,
    location: Optional[str] = None,
    description: Optional[str] = None
) -> Optional[str]:
    """Create a Microsoft Calendar event with full details."""
    url = "https://graph.microsoft.com/v1.0/me/events"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Ensure datetime has timezone info - if not, assume UTC
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    
    # Microsoft expects ISO8601 format with timezone
    body = {
        "subject": title,
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC"
        }
    }
    
    # Add optional fields
    if description:
        body["body"] = {
            "contentType": "text",
            "content": description
        }
    if location:
        body["location"] = {
            "displayName": location
        }
    if attendees:
        body["attendees"] = [
            {
                "emailAddress": {"address": email},
                "type": "required"
            } for email in attendees
        ]
    
    try:
        response = httpx.post(url, headers=headers, json=body)
        response.raise_for_status()
        event_data = response.json()
        event_id = event_data.get("id")
        print(f"✅ Created Microsoft calendar event with ID: {event_id}")
        return event_id  # Return the Microsoft event ID
    except Exception as e:
        print(f"Error creating Microsoft calendar event: {e}")
        return None

def update_google_calendar_event(
    token: str, 
    event_id: str, 
    title: Optional[str] = None, 
    start_time: Optional[datetime] = None, 
    end_time: Optional[datetime] = None,
    description: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    location: Optional[str] = None
) -> Optional[str]:
    """Update a Google Calendar event and return the event ID."""
    url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    body = {}
    if title:
        body["summary"] = title
    if start_time and end_time:
        body["start"] = {"dateTime": start_time.isoformat(), "timeZone": "UTC"}
        body["end"] = {"dateTime": end_time.isoformat(), "timeZone": "UTC"}
    if description:
        body["description"] = description
    if attendees:
        body["attendees"] = [{"email": email} for email in attendees]
    if location:
        body["location"] = location
    
    if not body:
        return event_id  # Nothing to update, return original ID
        
    try:
        response = httpx.patch(url, headers=headers, json=body)
        response.raise_for_status()
        event_data = response.json()
        updated_event_id = event_data.get("id", event_id)
        print(f"✅ Updated Google calendar event with ID: {updated_event_id}")
        return updated_event_id
    except Exception as e:
        print(f"Error updating Google calendar event: {e}")
        return None

def update_microsoft_calendar_event(
    token: str, 
    event_id: str, 
    title: Optional[str] = None, 
    start_time: Optional[datetime] = None, 
    end_time: Optional[datetime] = None,
    description: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    location: Optional[str] = None
) -> Optional[str]:
    """Update a Microsoft Calendar event and return the event ID."""
    url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    body = {}
    if title:
        body["subject"] = title
    if start_time and end_time:
        body["start"] = {"dateTime": start_time.isoformat(), "timeZone": "UTC"}
        body["end"] = {"dateTime": end_time.isoformat(), "timeZone": "UTC"}
    if description:
        body["body"] = {"contentType": "text", "content": description}
    if attendees:
        body["attendees"] = [{"emailAddress": {"address": email}, "type": "required"} for email in attendees]
    if location:
        body["location"] = {"displayName": location}
        
    if not body:
        return event_id  # Nothing to update, return original ID
    
    try:
        response = httpx.patch(url, headers=headers, json=body)
        response.raise_for_status()
        event_data = response.json()
        updated_event_id = event_data.get("id", event_id)
        print(f"✅ Updated Microsoft calendar event with ID: {updated_event_id}")
        return updated_event_id
    except Exception as e:
        print(f"Error updating Microsoft calendar event: {e}")
        return None

def delete_google_calendar_event(token: str, event_id: str) -> bool:
    url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = httpx.delete(url, headers=headers)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error deleting Google calendar event: {e}")
        return False

def delete_microsoft_calendar_event(token: str, event_id: str) -> bool:
    url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = httpx.delete(url, headers=headers)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error deleting Microsoft calendar event: {e}")
        return False