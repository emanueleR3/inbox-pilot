import os
import base64
import hashlib
from cryptography.fernet import Fernet

from datetime import datetime, timedelta
from typing import List, Optional
import httpx

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
    url = "https://www.googleapis.com/calendar/v3/freeBusy"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {
        "timeMin": start_time.isoformat() + "Z",
        "timeMax": end_time.isoformat() + "Z",
        "items": [{"id": "primary"}]
    }
    
    try:
        response = httpx.post(url, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()
        busy = data.get("calendars", {}).get("primary", {}).get("busy", [])
        slots = []
        for slot in busy:
            start = datetime.fromisoformat(slot["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(slot["end"].replace("Z", "+00:00"))
            slots.append((start, end))
        return slots
    except Exception as e:
        print(f"Error fetching Google calendar: {e}")
        return []

def get_microsoft_busy_slots(token: str, start_time: datetime, end_time: datetime) -> List[tuple]:
    url = "https://graph.microsoft.com/v1.0/me/calendar/getSchedule"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "outlook.timezone=\"UTC\""
    }
    body = {
        "schedules": ["me"],
        "startTime": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC"
        },
        "endTime": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC"
        },
        "availabilityViewInterval": 15
    }
    
    try:
        response = httpx.post(url, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()
        # Microsoft structure is slightly different, need to parse 'value' -> 'scheduleItems'
        # Assuming 'value' is list of schedules
        schedules = data.get("value", [])
        slots = []
        for schedule in schedules:
            items = schedule.get("scheduleItems", [])
            for item in items:
                if item["status"] != "free":
                    start = datetime.fromisoformat(item["start"]["dateTime"])
                    end = datetime.fromisoformat(item["end"]["dateTime"])
                    slots.append((start, end))
        return slots
    except Exception as e:
        print(f"Error fetching Microsoft calendar: {e}")
        return []

def calculate_free_slots(
    start_time: datetime, 
    end_time: datetime, 
    busy_slots: List[tuple], 
    opening_hrs: str, 
    working_days: List[int], 
    duration: int,
    not_available_dates: Optional[List[str]]
) -> List[str]:
    
    print("\n====== DEBUG calculate_free_slots() START ======")
    print(f"start_time: {start_time}")
    print(f"end_time:   {end_time}")
    print(f"opening_hrs: {opening_hrs}")
    print(f"working_days: {working_days}")
    print(f"duration: {duration}")
    print(f"busy_slots: {len(busy_slots)} items")
    print(f"not_available_dates: {not_available_dates}")
    print("================================================\n")

    free_slots = []
    current_time = start_time
    
    # Parse opening hours
    try:
        open_str, close_str = opening_hrs.split("-")
        open_h, open_m = map(int, open_str.split(":"))
        close_h, close_m = map(int, close_str.split(":"))
    except ValueError:
        print(f"❌ Invalid opening_hrs format: {opening_hrs}")
        return []

    # Normalize not_available_dates
    not_avail_set = set(not_available_dates or [])

    while current_time + timedelta(minutes=duration) <= end_time:

        print(f"\n[ITER] Checking: {current_time}")

        # Not working day
        if current_time.weekday() not in working_days:
            print(f"  ⛔ Skipped: not working day (weekday={current_time.weekday()})")
            current_time += timedelta(days=1)
            current_time = current_time.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
            continue
        
        # Day rejected
        if current_time.strftime("%Y-%m-%d") in not_avail_set:
            print(f"  ⛔ Skipped: date rejected ({current_time.strftime('%Y-%m-%d')})")
            current_time += timedelta(days=1)
            current_time = current_time.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
            continue
        
        # Opening hours
        day_open = current_time.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
        day_close = current_time.replace(hour=close_h, minute=close_m, second=0, microsecond=0)
        slot_end = current_time + timedelta(minutes=duration)

        if current_time < day_open:
            print(f"  ⛔ Before opening: {day_open}")
            current_time = day_open
            continue

        if slot_end > day_close:
            print(f"  ⛔ After closing: slot ends {slot_end}, close={day_close}")
            current_time += timedelta(days=1)
            current_time = current_time.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
            continue

        # Busy slot overlap
        is_busy = False
        for (b_start, b_end) in busy_slots:
            if current_time.replace(tzinfo=None) < b_end.replace(tzinfo=None) and \
               slot_end.replace(tzinfo=None) > b_start.replace(tzinfo=None):
                print(f"  ⛔ Overlaps busy: {b_start} -> {b_end}")
                is_busy = True
                break

        if not is_busy:
            print(f"  ✅ FREE SLOT: {current_time.isoformat()}")
            free_slots.append(current_time.isoformat())
            if len(free_slots) >= 3:
                print("=== RETURNING FIRST 3 FREE SLOTS ===")
                return free_slots
            current_time += timedelta(minutes=duration)
        else:
            print("  ↪ Moving forward 15 minutes")
            current_time += timedelta(minutes=15)

    print("=== END — Returning free_slots ===")
    return free_slots


def create_google_calendar_event(token: str, title: str, start_time: datetime, end_time: datetime) -> Optional[str]:
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {
        "summary": title,
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC"
        }
    }
    
    try:
        response = httpx.post(url, headers=headers, json=body)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error creating Google calendar event: {e}")
        return False

def create_microsoft_calendar_event(token: str, title: str, start_time: datetime, end_time: datetime) -> bool:
    url = "https://graph.microsoft.com/v1.0/me/events"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
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
    
    try:
        response = httpx.post(url, headers=headers, json=body)
        response.raise_for_status()
        return True
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
    attendees: Optional[List[str]] = None
) -> bool:
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
    
    if not body:
        return True # Nothing to update
        
    try:
        response = httpx.patch(url, headers=headers, json=body)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error updating Google calendar event: {e}")
        return False

def update_microsoft_calendar_event(
    token: str, 
    event_id: str, 
    title: Optional[str] = None, 
    start_time: Optional[datetime] = None, 
    end_time: Optional[datetime] = None,
    description: Optional[str] = None,
    attendees: Optional[List[str]] = None
) -> bool:
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
        
    if not body:
        return True # Nothing to update
    
    try:
        response = httpx.patch(url, headers=headers, json=body)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error updating Microsoft calendar event: {e}")
        return False

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