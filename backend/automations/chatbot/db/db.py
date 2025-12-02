import os
from dotenv import load_dotenv
from supabase import create_client, Client 
from threading import Lock
from typing import Optional, Dict, Any, List

load_dotenv()

_supabase_client: Client | None = None
_client_lock = Lock()

def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        with _client_lock:
            if _supabase_client is None: 
                url = os.getenv("SUPABASE_URL")
                key = os.getenv("SUPABASE_KEY")
                if not url or not key:
                    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
                _supabase_client = create_client(url, key)
    return _supabase_client


def get_user_context(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve comprehensive user context from Supabase including subscriptions and services.
    
    Args:
        user_id: The user identifier (auth user id)
        
    Returns:
        Dictionary containing user info, subscriptions, and services configuration.
        None if user not found or error occurs.
    """
    try:
        supabase = get_supabase_client()
        
        # 1. Get user's subscriptions from the junction table
        subscriptions_link = supabase.table("users_has_subscriptions").select(
            "subscription_id"
        ).eq("user_id", user_id).execute()
        
        if not subscriptions_link.data:
            print(f"No subscriptions found for user_id: {user_id}")
            return None
        
        subscription_ids = [row["subscription_id"] for row in subscriptions_link.data]
        
        # 2. Get subscription details
        subscriptions_response = supabase.table("subscriptions").select(
            "subscription_id, name, vat_number, city, address, active, plan"
        ).in_("subscription_id", subscription_ids).execute()
        
        subscriptions = subscriptions_response.data if subscriptions_response.data else []
        
        # 3. Get subscription services (email accounts and configurations)
        services_response = supabase.table("subscription_services").select(
            "service_id, "
            "subscription_id, "
            "email, "
            "email_provider, "
            "calendar_provider, "
            "calendar_names, "
            "information, "
            "imap_server, "
            "smtp_server, "
            "confidence_response_threshold, "
            "confidence_review_mail, "
            "priority_threshold, "
            "confidence_classification_threshold, "
            "urgent_meeting_threshold, "
            "activated, "
            "config_completed, "
            "quiz_q_a"
        ).in_("subscription_id", subscription_ids).execute()
        
        services = services_response.data if services_response.data else []
        
        # Build user context
        user_context = {
            "user_id": user_id,
            "subscriptions": [],
            "configured_emails": [],
            "summary": ""
        }
        
        # Process subscriptions
        for sub in subscriptions:
            sub_info = {
                "subscription_id": sub.get("subscription_id"),
                "company_name": sub.get("name"),
                "vat_number": sub.get("vat_number"),
                "city": sub.get("city"),
                "address": sub.get("address"),
                "active": sub.get("active"),
                "plan": sub.get("plan"),
                "services": []
            }
            
            # Add related services to this subscription
            for service in services:
                if service.get("subscription_id") == sub.get("subscription_id"):
                    service_info = {
                        "email": service.get("email"),
                        "email_provider": service.get("email_provider"),
                        "calendar_provider": service.get("calendar_provider"),
                        "calendar_names": service.get("calendar_names"),
                        "information": service.get("information"),
                        "activated": service.get("activated"),
                        "config_completed": service.get("config_completed"),
                        "quiz_q_a": service.get("quiz_q_a")
                    }
                    sub_info["services"].append(service_info)
                    
                    # Track configured emails for quick access
                    if service.get("email") and service.get("activated"):
                        user_context["configured_emails"].append(service.get("email"))
            
            user_context["subscriptions"].append(sub_info)
        
        # Build a summary text for the chatbot context
        summary_parts = []
        for sub in user_context["subscriptions"]:
            company = sub.get("company_name", "Unknown Company")
            summary_parts.append(f"Company: {company}")
            if sub.get("city"):
                summary_parts.append(f"  Location: {sub.get('city')}, {sub.get('address', '')}")
            if sub.get("plan"):
                summary_parts.append(f"  Plan: {sub.get('plan')}")
            
            if sub.get("services"):
                summary_parts.append("  Configured email accounts:")
                for svc in sub["services"]:
                    email = svc.get("email", "N/A")
                    provider = svc.get("email_provider", "unknown")
                    calendar = svc.get("calendar_provider", "none")
                    status = "active" if svc.get("activated") else "inactive"
                    summary_parts.append(f"    - {email} ({provider}, calendar: {calendar}, status: {status})")
                    
                    # Include custom information if available
                    if svc.get("information"):
                        info = svc.get("information")
                        if isinstance(info, dict):
                            for key, value in info.items():
                                summary_parts.append(f"      {key}: {value}")
        
        user_context["summary"] = "\n".join(summary_parts)
        
        print(f"✅ [DB] User context retrieved for user_id: {user_id}")
        return user_context
        
    except Exception as e:
        print(f"❌ [DB] Error retrieving user context for {user_id}: {str(e)}")
        return None