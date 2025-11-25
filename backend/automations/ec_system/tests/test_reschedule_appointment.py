"""
Test script for reschedule_appointment tool.

This script tests the _reschedule_appointment_tool using real database connections
and calendar provider credentials from subscription_services table.

Usage:
    python test_reschedule_appointment.py
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
from db_client import get_supabase_client, get_scheduled_event_by_code
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
    
    # Query subscription_services table
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

    return config


def test_reschedule_appointment(event_code: str, new_date: str = None):
    """
    Test the reschedule_appointment tool.
    
    Args:
        event_code: Event code to reschedule
        new_date: New date/time in format YYYY-MM-DDThh:mm:ss
                 If None, reschedules to 2 days from now at 14:00
    """
    print("\n" + "="*60)
    print("🧪 TEST: reschedule_appointment tool")
    print("="*60)
    
    # Step 1: Get event from database
    print(f"\n📋 Retrieving event with code: {event_code}")
    event = get_scheduled_event_by_code(event_code)
    
    if not event:
        print(f"❌ Event with code {event_code} not found in database")
        return None
    
    print(f"✅ Event found:")
    print(f"   - Title: {event.get('title')}")
    print(f"   - Provider Event ID: {event.get('provider_event_id')}")
    print(f"   - Service ID: {event.get('service_id')}")
    
    # Step 2: Prepare new appointment details
    if new_date is None:
        # Default: 2 days from now at 14:00
        target_date = datetime.now() + timedelta(days=2)
        new_date = target_date.replace(hour=14, minute=0, second=0, microsecond=0).isoformat()
    
    new_title = "[TEST - RESCHEDULED] Appointment from test script"
    new_duration = 90  # Change duration to 90 minutes
    new_attendees = ["test@example.com"]
    new_place = "Updated Test Location"
    additional_notes = "This appointment was rescheduled by test_reschedule_appointment.py"
    
    print(f"\n📝 New Appointment Details:")
    print(f"   - event_code: {event_code}")
    print(f"   - new_title: {new_title}")
    print(f"   - new_date: {new_date}")
    print(f"   - new_duration: {new_duration} minutes")
    print(f"   - new_attendees: {new_attendees}")
    print(f"   - new_place: {new_place}")
    print(f"   - additional_notes: {additional_notes}")
    
    try:
        # Call the reschedule tool
        result = llm_client._reschedule_appointment_tool(
            event_code=event_code,
            new_title=new_title,
            new_date=new_date,
            new_duration=new_duration,
            new_attendees=new_attendees,
            new_place=new_place,
            additional_notes=additional_notes
        )
        
        print(f"\n✅ Result:")
        print(f"   - scheduled: {result.get('scheduled')}")
        print(f"   - overlap: {result.get('overlap')}")
        print(f"   - invalid_event_code: {result.get('invalid_event_code', False)}")
        
        if result.get('invalid_event_code'):
            print(f"\n❌ Invalid event code provided")
        elif result.get('scheduled'):
            print(f"\n🎉 Appointment rescheduled successfully!")
            print(f"   Event code: {event_code} (unchanged)")
            print(f"   Check your calendar to verify the changes")
        elif result.get('overlap'):
            print(f"\n⚠️ Cannot reschedule: new time slot overlaps with existing event")
        else:
            print(f"\n❌ Rescheduling failed")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error testing reschedule_appointment: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main test function."""
    print("\n" + "="*60)
    print("🚀 RESCHEDULE APPOINTMENT TEST")
    print("="*60)
    
    # Configuration
    test_email = "INSERT_MAIL"
    test_event_code = "107889"  # Event code to reschedule
    
    # Step 1: Get service configuration from database
    config = get_service_config(test_email)
    
    if not config:
        print("\n❌ Cannot proceed without service configuration")
        return
    
    # Step 2: Test reschedule_appointment
    print("\n" + "-"*60)
    
    # You can customize the new date here, or pass None to use default (2 days from now at 14:00)
    # Example: new_date = "2025-11-26T15:30:00"
    new_date = None
    
    result = test_reschedule_appointment(test_event_code, new_date)
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    if result:
        print(f"\n✅ reschedule_appointment: {'SUCCESS' if result.get('scheduled') else 'FAILED'}")
        if result.get('scheduled'):
            print(f"\n🎯 Rescheduled event code: {test_event_code}")
            print(f"   Verify the changes in your Google Calendar")
    else:
        print(f"\n❌ Test failed to execute")
    
    print("\n" + "="*60)
    print("✅ Test completed")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
