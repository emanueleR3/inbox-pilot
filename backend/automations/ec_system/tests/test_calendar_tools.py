"""
Test script for calendar booking tools (book_appointment and propose_new_slots).

This script tests the two LLM tools using real database connections
and calendar provider credentials from subscription_services table.

Usage:
    python test_calendar_tools.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

# Import required modules
from db_client import get_supabase_client
from ec_system.utils.utils import decrypt
from ec_system.llm.client import llm_client


def get_service_config(email: str):
    """
    Retrieve service configuration and credentials from database.
    
    Args:
        email: User email to lookup in subscription_services
        
    Returns:
        dict: Service configuration with decrypted token
    """
    print(f"\n🔍 Retrieving service configuration for: {email}")
    
    supabase = get_supabase_client()
    
    # Query subscription_services table (no opening_hrs, working_days, appointment_duration)
    response = supabase.table("subscription_services").select(
        "service_id, subscription_id, email, calendar_provider, hashed_access_token"
    ).eq("email", email).execute()

    if not response.data:
        print(f"❌ No service configuration found for email: {email}")
        return None

    if len(response.data) > 1:
        print(f"⚠️ Multiple configurations found, using first one")

    data = response.data[0]

    # Decrypt access token
    hashed_token = data.get("hashed_access_token")
    if not hashed_token:
        print(f"❌ No hashed access token found")
        return None

    try:
        decrypted_token = decrypt(hashed_token, "token")
        print(f"✅ Token decrypted successfully")
    except Exception as e:
        print(f"❌ Error decrypting token: {e}")
        return None

    # Query subscriptions table for business_hours and appointment_duration
    business_hours = None
    appointment_duration = None
    subscription_id = data.get("subscription_id")
    if subscription_id:
        sub_resp = supabase.table("subscriptions").select(
            "business_hours, appointment_duration"
        ).eq("subscription_id", subscription_id).execute()
        if sub_resp.data:
            sub_data = sub_resp.data[0]
            business_hours = sub_data.get("business_hours")
            appointment_duration = sub_data.get("appointment_duration")

    config = {
        "service_id": data.get("service_id"),
        "subscription_id": subscription_id,
        "email": data.get("email"),
        "calendar_provider": data.get("calendar_provider"),
        "access_token": decrypted_token,
        "business_hours": business_hours,
        "appointment_duration": appointment_duration
    }

    print(f"📋 Service Configuration:")
    print(f"   - service_id: {config['service_id']}")
    print(f"   - calendar_provider: {config['calendar_provider']}")
    print(f"   - business_hours: {config['business_hours']}")
    print(f"   - appointment_duration: {config['appointment_duration']}")

    return config


def test_propose_new_slots(service_id: str):
    """
    Test the propose_new_slots tool.
    
    Args:
        service_id: Service ID from subscription_services
    """
    print("\n" + "="*60)
    print("🧪 TEST 1: propose_new_slots tool")
    print("="*60)
    
    # Test parameters
    favorite_day = None  # No preference
    not_available_dates = []  # No rejected dates
    
    print(f"\n📝 Test Parameters:")
    print(f"   - service_id: {service_id}")
    print(f"   - favorite_day: {favorite_day}")
    print(f"   - not_available_dates: {not_available_dates}")
    
    try:
        # Call the tool
        result = llm_client._propose_new_slots_tool(
            service_id=service_id,
            favorite_day=favorite_day,
            not_available_dates=not_available_dates
        )
        
        print(f"\n✅ Result: {len(result)} slots proposed")
        for i, slot in enumerate(result, 1):
            print(f"   {i}. {slot}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error testing propose_new_slots: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_book_appointment(service_id: str, test_date: str = None):
    """
    Test the book_appointment tool.
    
    Args:
        service_id: Service ID from subscription_services
        test_date: Optional test date in format YYYY-MM-DDThh:mm:ss
                  If None, uses tomorrow at 10:00
    """
    print("\n" + "="*60)
    print("🧪 TEST 2: book_appointment tool")
    print("="*60)
    
    # Test parameters
    if test_date is None:
        # Default: tomorrow at 10:00
        tomorrow = datetime.now() + timedelta(days=1)
        test_date = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0).isoformat()
    
    title = "[TEST] Appointment from test script"
    duration = 60  # minutes
    event_type = "test_event"
    created_by = "INSERT_MAIL"
    thread_id = None
    attendees = ["test.attendee@example.com", "another.attendee@example.com"]
    place = "Test Location - Conference Room A"
    additional_notes = "This is a test appointment created by test_calendar_tools.py with full event details (attendees, location, description)."
    
    print(f"\n📝 Test Parameters:")
    print(f"   - service_id: {service_id}")
    print(f"   - thread_id: {thread_id}")
    print(f"   - title: {title}")
    print(f"   - date: {test_date}")
    print(f"   - duration: {duration} minutes")
    print(f"   - event_type: {event_type}")
    print(f"   - created_by: {created_by}")
    print(f"   - attendees: {attendees}")
    print(f"   - place: {place}")
    print(f"   - additional_notes: {additional_notes}")
    
    try:
        # Call the tool
        result = llm_client._book_appointment_tool(
            title_of_event=title,
            date=test_date,
            duration=duration,
            service_id=service_id,
            event_type=event_type,
            created_by=created_by,
            thread_id=thread_id,
            attendees=attendees,
            place=place,
            additional_notes=additional_notes
        )
        
        print(f"\n✅ Result:")
        print(f"   - scheduled: {result.get('scheduled')}")
        print(f"   - overlap: {result.get('overlap')}")
        print(f"   - event_code: {result.get('event_code')}")
        
        if result.get('scheduled'):
            print(f"\n🎉 Appointment booked successfully!")
            print(f"   Event code: {result.get('event_code')}")
        elif result.get('overlap'):
            print(f"\n⚠️ Cannot book: time slot overlaps with existing event")
        else:
            print(f"\n❌ Booking failed")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error testing book_appointment: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main test function."""
    print("\n" + "="*60)
    print("🚀 CALENDAR TOOLS TEST SUITE")
    print("="*60)
    
    # Configuration
    test_email = "INSERT_MAIL"
    
    # Step 1: Get service configuration from database
    config = get_service_config(test_email)
    
    if not config:
        print("\n❌ Cannot proceed without service configuration")
        return
    
    service_id = config["service_id"]
    
    # Step 2: Test propose_new_slots
    print("\n" + "-"*60)
    proposed_slots = test_propose_new_slots(service_id)
    
    # Step 3: Test book_appointment
    print("\n" + "-"*60)
    
    # Option 1: Use a proposed slot if available
    if proposed_slots and len(proposed_slots) > 0:
        test_date = proposed_slots[0]  # Use first proposed slot
        print(f"\n💡 Using first proposed slot for booking test: {test_date}")
    else:
        test_date = None  # Use default (tomorrow at 10:00)
        print(f"\n💡 Using default date for booking test (tomorrow at 10:00)")
    
    booking_result = test_book_appointment(service_id, test_date)
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"\n✅ propose_new_slots: {len(proposed_slots) if proposed_slots else 0} slots found")
    print(f"✅ book_appointment: {'SUCCESS' if booking_result and booking_result.get('scheduled') else 'FAILED'}")
    
    if booking_result and booking_result.get('event_code'):
        print(f"\n🎯 Created event code: {booking_result.get('event_code')}")
        print(f"   You can verify this event in your calendar")
    
    print("\n" + "="*60)
    print("✅ All tests completed")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
