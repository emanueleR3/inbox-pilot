import datetime
import httpx
from db import db
from utils import utils
from typing import List, Optional
from supabase import Client

def create_calendar_event(title: str, date: str, time: str, duration: int) -> str:
    """Create a calendar event."""
    print(f"Creating calendar event '{title}' on {date} at {time} for {duration} minutes")
    return f"Calendar event '{title}' created on {date} at {time} for {duration} minutes."

def edit_calendar_event(event_id: str, title: Optional[str] = None, date: Optional[str] = None, time: Optional[str] = None, duration: Optional[int] = None) -> str:
    """Edit a calendar event."""
    print(f"Editing calendar event '{event_id}' with title '{title}', date '{date}', time '{time}', duration '{duration}'")
    return f"Calendar event '{event_id}' edited."

def delete_calendar_event(event_id: str) -> str:
    """Delete a calendar event."""
    print(f"Deleting calendar event '{event_id}'")
    return f"Calendar event '{event_id}' deleted."


def propose_new_slots(email: str, favourite_day: Optional[str] = None, not_available_dates: Optional[List[str]] = None) -> List[str]:
    supabase: Client = db.get_supabase_client()
    
    response_sub_ser = supabase.table("subscription_services").select("subscription_id, calendar_provider, hash_token").where("email", email).execute()

    if not response_sub_ser.data:
        print("No subscription service data found.")
        return []

    data = response_sub_ser.data[0]
    calendar_provider = data.get("calendar_provider")
    hash_token = data.get("hash_token")
    subscription_id = data.get("subscription_id")

    response_sub = supabase.table("subscriptions").select("opening_hrs, working_days, appointament_duration").where("subscription_id", subscription_id).execute()

    if not response_sub.data:
        print("No subscription data found.")
        return []
    
    opening_hrs = response_sub.data[0].get("opening_hrs") 
    working_days = response_sub.data[0].get("working_days") 
    appointment_duration = response_sub.data[0].get("appointament_duration") # in minutes
    
    if not hash_token:
        print("No hash token found.")
        return []

    token = utils.decrypt(hash_token, "token")
    
    if not token:
        print("Failed to decrypt token.")
        return []

    now = datetime.datetime.now()
    start_time = now
    end_time = now + datetime.timedelta(days=7) # Look ahead 7 days by default
    
    if favourite_day:
        try:
            fav_date = datetime.datetime.strptime(favourite_day, "%Y-%m-%d")
            start_time = fav_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = fav_date.replace(hour=23, minute=59, second=59, microsecond=0)

            if start_time < now:
                 start_time = now
        except ValueError:
            print(f"Invalid favourite_day format: {favourite_day}")
            pass

    busy_slots = []
    
    if calendar_provider == "google":
        busy_slots = utils.get_google_busy_slots(token, start_time, end_time)
    elif calendar_provider == "microsoft":
        busy_slots = utils.get_microsoft_busy_slots(token, start_time, end_time)
    else:
        print(f"Unknown calendar provider: {calendar_provider}")
        return []

    free_slots = utils.calculate_free_slots(
        start_time, 
        end_time, 
        busy_slots, 
        opening_hrs, 
        working_days, 
        appointment_duration, 
        not_available_dates
    )

    supabase.close()
    
    return free_slots[:3]