import datetime
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo
import httpx
from typing import List, Optional, Dict, Any, Tuple

# Use absolute imports for the chatbot module
from automations.ec_system.utils.utils import (
    decrypt,
    get_google_busy_slots,
    get_microsoft_busy_slots,
    calculate_free_slots,
    create_google_calendar_event,
    create_microsoft_calendar_event
)


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
    from automations.chatbot.db.db import get_calendar_appointment_info
    
    # Get calendar appointment info from db.py
    data = get_calendar_appointment_info(email)
    
    if not data:
        print("No subscription service data found.")
        return []

    calendar_provider = data.get("calendar_provider")
    hashed_access_token = data.get("hashed_access_token")
    subscription_id = data.get("subscription_id")
    business_hours = data.get("business_hours")
    appointment_duration = data.get("appointment_duration") # in minutes 
    
    if not hashed_access_token:
        print("No access token found.")
        return []

    token = decrypt(hashed_access_token, "token")
    
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
        busy_slots = get_google_busy_slots(token, start_time, end_time)
    elif calendar_provider == "microsoft":
        busy_slots = get_microsoft_busy_slots(token, start_time, end_time)
    else:
        print(f"Unknown calendar provider: {calendar_provider}")
        return []

    free_slots = calculate_free_slots(
        start_time, 
        end_time, 
        busy_slots, 
        business_hours,  
        appointment_duration, 
        not_available_dates
    )
    
    return free_slots[:3]


def _intersect_business_hours(participants_hours: List[Dict[str, List[str]]]) -> Dict[str, List[str]]:
    """
    Calculate the intersection of business hours across multiple participants.
    
    Each participant has business_hours in format: {"0": ["09:00-17:00"], "1": ["09:00-13:00", "14:00-18:00"], ...}
    This function finds the overlapping time slots when ALL participants are available.
    
    Args:
        participants_hours: List of business_hours dictionaries from each participant
        
    Returns:
        Dictionary with intersected business hours (same format)
    """
    if not participants_hours:
        return {}
    
    if len(participants_hours) == 1:
        return participants_hours[0] or {}
    
    # Start with the first participant's hours
    result = {}
    first_hours = participants_hours[0] or {}
    
    # Get common working days (days present in ALL participants)
    common_days = set(first_hours.keys())
    for hours in participants_hours[1:]:
        if hours:
            common_days &= set(hours.keys())
        else:
            # If any participant has no hours defined, no common availability
            return {}
    
    # For each common day, intersect the time ranges
    for day in common_days:
        day_ranges = []
        
        for hours in participants_hours:
            if not hours or day not in hours:
                continue
            day_ranges.append(hours[day])
        
        if not day_ranges:
            continue
        
        # Convert to minutes for easier intersection
        def parse_range(time_range: str) -> Tuple[int, int]:
            """Parse '09:00-17:00' to (540, 1020) minutes from midnight."""
            start_str, end_str = time_range.split("-")
            start_h, start_m = map(int, start_str.split(":"))
            end_h, end_m = map(int, end_str.split(":"))
            return (start_h * 60 + start_m, end_h * 60 + end_m)
        
        def ranges_to_intervals(ranges: List[str]) -> List[Tuple[int, int]]:
            """Convert list of time ranges to list of minute intervals."""
            intervals = []
            for r in ranges:
                try:
                    intervals.append(parse_range(r))
                except (ValueError, AttributeError):
                    continue
            return intervals
        
        def intersect_intervals(intervals_list: List[List[Tuple[int, int]]]) -> List[Tuple[int, int]]:
            """Intersect multiple lists of intervals."""
            if not intervals_list:
                return []
            
            # Start with all minutes from the first participant's ranges
            # Use a set to track available minutes
            available_minutes = set()
            for start, end in intervals_list[0]:
                available_minutes.update(range(start, end))
            
            # Intersect with each subsequent participant
            for intervals in intervals_list[1:]:
                participant_minutes = set()
                for start, end in intervals:
                    participant_minutes.update(range(start, end))
                available_minutes &= participant_minutes
            
            if not available_minutes:
                return []
            
            # Convert back to intervals
            sorted_minutes = sorted(available_minutes)
            result_intervals = []
            start = sorted_minutes[0]
            prev = start
            
            for minute in sorted_minutes[1:]:
                if minute != prev + 1:
                    result_intervals.append((start, prev + 1))
                    start = minute
                prev = minute
            result_intervals.append((start, prev + 1))
            
            return result_intervals
        
        def interval_to_string(interval: Tuple[int, int]) -> str:
            """Convert (540, 1020) to '09:00-17:00'."""
            start_h, start_m = divmod(interval[0], 60)
            end_h, end_m = divmod(interval[1], 60)
            return f"{start_h:02d}:{start_m:02d}-{end_h:02d}:{end_m:02d}"
        
        # Get all intervals for this day from all participants
        all_intervals = [ranges_to_intervals(ranges) for ranges in day_ranges]
        
        # Intersect them
        intersected = intersect_intervals(all_intervals)
        
        if intersected:
            result[day] = [interval_to_string(i) for i in intersected]
    
    return result


def find_common_free_slots(
    participants: List[Dict[str, Any]], 
    duration_minutes: int, 
    days_ahead: int = 10,
    preferred_datetime: Optional[str] = None,
    user_timezone: str = "Europe/Rome"
) -> Dict[str, Any]:
    """
    Find common free time slots across multiple participants' calendars.
    
    This function retrieves busy slots from all participants' calendars (Google or Microsoft),
    combines them, and calculates free slots that work for everyone within their business hours.
    
    Args:
        participants: List of participant dictionaries, each containing:
            - email: str
            - name: str (optional)
            - calendar_provider: 'google' or 'microsoft'
            - hashed_access_token: encrypted OAuth token
            - business_hours: dict like {"0": ["09:00-17:00"], ...}
        duration_minutes: Required meeting duration in minutes
        days_ahead: Number of days to search ahead (default: 10)
        preferred_datetime: Optional ISO format datetime to check specifically
        user_timezone: Timezone for calculations (default: Europe/Rome)
        
    Returns:
        Dictionary with:
        - 'free_slots': List of ISO datetime strings representing available start times
        - 'calendar_errors': List of emails where calendar access failed
        - 'error': General error message if any
    """
    result = {
        "free_slots": [],
        "calendar_errors": [],
        "error": None
    }
    
    if not participants:
        result["error"] = "No participants provided"
        return result
    
    try:
        tz = ZoneInfo(user_timezone)
        now = datetime.datetime.now(tz)
        
        # Define search range
        if preferred_datetime:
            try:
                # Parse preferred datetime and search within that day
                preferred_dt = datetime.datetime.fromisoformat(preferred_datetime.replace("Z", "+00:00"))
                if preferred_dt.tzinfo is None:
                    preferred_dt = preferred_dt.replace(tzinfo=tz)
                else:
                    preferred_dt = preferred_dt.astimezone(tz)
                
                start_time = preferred_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(days=1)
                
                # Don't search in the past
                if start_time < now:
                    start_time = now
            except ValueError:
                result["error"] = f"Invalid preferred_datetime format: {preferred_datetime}"
                return result
        else:
            start_time = now
            end_time = now + timedelta(days=days_ahead)
        
        # Collect all busy slots from all participants
        all_busy_slots = []
        all_business_hours = []
        
        for participant in participants:
            email = participant.get("email", "unknown")
            calendar_provider = participant.get("calendar_provider")
            hashed_access_token = participant.get("hashed_access_token")
            business_hours = participant.get("business_hours")
            
            if not hashed_access_token:
                print(f"⚠️ [CALENDAR] No access token for {email}, skipping")
                result["calendar_errors"].append(email)
                continue
            
            # Decrypt the token
            try:
                token = decrypt(hashed_access_token, "token")
                if not token:
                    raise ValueError("Decryption returned empty token")
            except Exception as e:
                print(f"⚠️ [CALENDAR] Failed to decrypt token for {email}: {e}")
                result["calendar_errors"].append(email)
                continue
            
            # Get busy slots based on provider
            try:
                if calendar_provider == "google":
                    busy_slots = get_google_busy_slots(token, start_time, end_time)
                elif calendar_provider == "microsoft":
                    busy_slots = get_microsoft_busy_slots(token, start_time, end_time)
                else:
                    print(f"⚠️ [CALENDAR] Unknown provider '{calendar_provider}' for {email}")
                    result["calendar_errors"].append(email)
                    continue
                
                all_busy_slots.extend(busy_slots)
                print(f"✅ [CALENDAR] Retrieved {len(busy_slots)} busy slots for {email}")
                
            except Exception as e:
                print(f"⚠️ [CALENDAR] Error fetching calendar for {email}: {e}")
                result["calendar_errors"].append(email)
                continue
            
            # Collect business hours
            if business_hours:
                all_business_hours.append(business_hours)
            else:
                # Default business hours: Monday-Friday 9:00-18:00
                default_hours = {str(d): ["09:00-18:00"] for d in range(5)}
                all_business_hours.append(default_hours)
        
        # Check if we have at least one valid participant
        valid_participants = len(participants) - len(result["calendar_errors"])
        if valid_participants == 0:
            result["error"] = "Could not access any participant's calendar"
            return result
        
        # Intersect business hours across all participants
        intersected_hours = _intersect_business_hours(all_business_hours)
        
        if not intersected_hours:
            result["error"] = "No common working hours found between participants"
            return result
        
        # Calculate free slots using the combined busy slots and intersected hours
        free_slots = calculate_free_slots(
            start_time=start_time,
            end_time=end_time,
            busy_slots=all_busy_slots,
            business_hours=intersected_hours,
            duration=duration_minutes,
            not_available_dates=None,
            user_timezone=user_timezone
        )
        
        result["free_slots"] = free_slots
        print(f"✅ [CALENDAR] Found {len(free_slots)} common free slots")
        
        return result
        
    except Exception as e:
        result["error"] = f"Error calculating free slots: {str(e)}"
        print(f"❌ [CALENDAR] {result['error']}")
        return result


def check_slot_availability(
    participants: List[Dict[str, Any]],
    slot_datetime: str,
    duration_minutes: int,
    user_timezone: str = "Europe/Rome"
) -> Dict[str, Any]:
    """
    Check if a specific time slot is available for all participants.
    
    Args:
        participants: List of participant dictionaries (same format as find_common_free_slots)
        slot_datetime: ISO format datetime to check
        duration_minutes: Meeting duration in minutes
        user_timezone: Timezone for calculations
        
    Returns:
        Dictionary with:
        - 'available': True if all participants are free
        - 'conflicts': List of emails that have conflicts
        - 'calendar_errors': List of emails where calendar access failed
        - 'error': Error message if any
    """
    result = {
        "available": False,
        "conflicts": [],
        "calendar_errors": [],
        "error": None
    }
    
    try:
        tz = ZoneInfo(user_timezone)
        
        # Parse the slot datetime
        slot_start = datetime.datetime.fromisoformat(slot_datetime.replace("Z", "+00:00"))
        if slot_start.tzinfo is None:
            slot_start = slot_start.replace(tzinfo=tz)
        else:
            slot_start = slot_start.astimezone(tz)
        
        slot_end = slot_start + timedelta(minutes=duration_minutes)
        
        for participant in participants:
            email = participant.get("email", "unknown")
            calendar_provider = participant.get("calendar_provider")
            hashed_access_token = participant.get("hashed_access_token")
            
            if not hashed_access_token:
                result["calendar_errors"].append(email)
                continue
            
            try:
                token = decrypt(hashed_access_token, "token")
                if not token:
                    result["calendar_errors"].append(email)
                    continue
            except Exception:
                result["calendar_errors"].append(email)
                continue
            
            # Check for conflicts in a small window around the slot
            check_start = slot_start - timedelta(hours=1)
            check_end = slot_end + timedelta(hours=1)
            
            try:
                if calendar_provider == "google":
                    busy_slots = get_google_busy_slots(token, check_start, check_end)
                elif calendar_provider == "microsoft":
                    busy_slots = get_microsoft_busy_slots(token, check_start, check_end)
                else:
                    result["calendar_errors"].append(email)
                    continue
                
                # Check for overlap with any busy slot
                for busy_slot in busy_slots:
                    # Handle both 2-tuple and 3-tuple formats
                    b_start = busy_slot[0]
                    b_end = busy_slot[1]
                    
                    # Convert to same timezone for comparison
                    if b_start.tzinfo is not None:
                        b_start = b_start.astimezone(tz)
                    if b_end.tzinfo is not None:
                        b_end = b_end.astimezone(tz)
                    
                    # Check overlap: slot overlaps if it doesn't end before busy starts AND doesn't start after busy ends
                    if slot_start < b_end and slot_end > b_start:
                        result["conflicts"].append(email)
                        break
                        
            except Exception as e:
                print(f"⚠️ [CALENDAR] Error checking availability for {email}: {e}")
                result["calendar_errors"].append(email)
        
        # Available only if no conflicts and at least one valid participant
        valid_participants = len(participants) - len(result["calendar_errors"])
        result["available"] = len(result["conflicts"]) == 0 and valid_participants > 0
        
        return result
        
    except Exception as e:
        result["error"] = f"Error checking availability: {str(e)}"
        return result


def schedule_calendar_event(
    organizer: Dict[str, Any],
    title: str,
    start_datetime: str,
    duration_minutes: int,
    attendees: Optional[List[str]] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    user_timezone: str = "Europe/Rome"
) -> Dict[str, Any]:
    """
    Create a calendar event for the organizer and optionally invite attendees.
    
    Args:
        organizer: Dictionary with organizer's calendar info (email, calendar_provider, hashed_access_token)
        title: Event title
        start_datetime: ISO format datetime for event start
        duration_minutes: Event duration in minutes
        attendees: Optional list of attendee email addresses
        description: Optional event description
        location: Optional event location
        user_timezone: Timezone for the event
        
    Returns:
        Dictionary with:
        - 'success': True if event was created
        - 'event_id': The created event's ID (if successful)
        - 'error': Error message if failed
    """
    result = {
        "success": False,
        "event_id": None,
        "error": None
    }
    
    try:
        tz = ZoneInfo(user_timezone)
        
        # Parse datetime
        start_dt = datetime.datetime.fromisoformat(start_datetime.replace("Z", "+00:00"))
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=tz)
        else:
            start_dt = start_dt.astimezone(tz)
        
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        
        # Get organizer's token
        hashed_access_token = organizer.get("hashed_access_token")
        calendar_provider = organizer.get("calendar_provider")
        
        if not hashed_access_token:
            result["error"] = "Organizer has no access token configured"
            return result
        
        token = decrypt(hashed_access_token, "token")
        if not token:
            result["error"] = "Failed to decrypt organizer's access token"
            return result
        
        # Create event based on provider
        if calendar_provider == "google":
            event_id = create_google_calendar_event(
                token=token,
                title=title,
                start_time=start_dt,
                end_time=end_dt,
                attendees=attendees,
                description=description,
                location=location
            )
        elif calendar_provider == "microsoft":
            event_id = create_microsoft_calendar_event(
                token=token,
                title=title,
                start_time=start_dt,
                end_time=end_dt,
                attendees=attendees,
                description=description,
                location=location
            )
        else:
            result["error"] = f"Unknown calendar provider: {calendar_provider}"
            return result
        
        if event_id:
            result["success"] = True
            result["event_id"] = event_id
            print(f"✅ [CALENDAR] Event '{title}' created with ID: {event_id}")
        else:
            result["error"] = "Failed to create calendar event"
        
        return result
        
    except Exception as e:
        result["error"] = f"Error creating event: {str(e)}"
        print(f"❌ [CALENDAR] {result['error']}")
        return result