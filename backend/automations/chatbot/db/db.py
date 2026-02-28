import os
from dotenv import load_dotenv
from supabase import create_client, Client 
from threading import Lock
from typing import Optional, Dict, Any, List, Tuple

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


def get_colleagues_by_subscription(user_email: str, search_terms: List[str]) -> Dict[str, Any]:
    """
    Retrieve colleagues from the same subscription (company) by searching their name or email.
    
    This function finds the user's subscription_id and then searches for colleagues
    within the same subscription, matching by name or email (case-insensitive).
    
    Args:
        user_email: The email of the current user to find their subscription
        search_terms: List of names or emails to search for
        
    Returns:
        Dictionary with keys:
        - 'exact_matches': List of uniquely identified colleagues
        - 'ambiguous_matches': Dict mapping search term to list of possible matches
        - 'not_found': List of search terms with no matches
        - 'error': Error message if any (None otherwise)
        
        Each colleague dict contains: name, email, calendar_provider, 
        hashed_access_token, business_hours
    """
    result = {
        "exact_matches": [],
        "ambiguous_matches": {},
        "not_found": [],
        "error": None
    }
    
    if not search_terms:
        return result
    
    try:
        supabase = get_supabase_client()
        
        # Step 1: Find the subscription_id for the current user
        user_response = supabase.table("subscription_services").select(
            "subscription_id"
        ).eq("email", user_email.lower()).execute()
        
        if not user_response.data:
            result["error"] = f"No subscription found for email: {user_email}"
            print(f"❌ [DB] {result['error']}")
            return result
        
        subscription_id = user_response.data[0].get("subscription_id")
        
        if not subscription_id:
            result["error"] = f"User {user_email} has no associated subscription_id"
            print(f"❌ [DB] {result['error']}")
            return result
        
        # Step 2: Get all colleagues in the same subscription
        colleagues_response = supabase.table("subscription_services").select(
            "name, email, calendar_provider, hashed_access_token, business_hours"
        ).eq("subscription_id", subscription_id).eq("activated", True).execute()
        
        if not colleagues_response.data:
            # No colleagues found at all
            result["not_found"] = search_terms.copy()
            return result
        
        all_colleagues = colleagues_response.data
        
        # Step 3: For each search term, find matching colleagues
        # Track which colleagues have been matched to avoid duplicates in exact_matches
        matched_emails = set()
        
        for term in search_terms:
            term_lower = term.lower().strip()
            matches = []
            
            for colleague in all_colleagues:
                colleague_name = (colleague.get("name") or "").lower()
                colleague_email = (colleague.get("email") or "").lower()
                
                # Skip the requesting user themselves
                if colleague_email == user_email.lower():
                    continue
                
                # Check if term matches name or email (case-insensitive partial match)
                name_match = term_lower in colleague_name
                email_match = term_lower in colleague_email or colleague_email == term_lower
                
                if name_match or email_match:
                    matches.append({
                        "name": colleague.get("name"),
                        "email": colleague.get("email"),
                        "calendar_provider": colleague.get("calendar_provider"),
                        "hashed_access_token": colleague.get("hashed_access_token"),
                        "business_hours": colleague.get("business_hours")
                    })
            
            # Classify the result
            if len(matches) == 0:
                result["not_found"].append(term)
            elif len(matches) == 1:
                # Unique match - add only if not already in exact_matches
                if matches[0]["email"] not in matched_emails:
                    result["exact_matches"].append(matches[0])
                    matched_emails.add(matches[0]["email"])
            else:
                # Ambiguous - multiple matches for this search term
                result["ambiguous_matches"][term] = [m["email"] for m in matches]
        
        print(f"✅ [DB] Colleagues search completed: {len(result['exact_matches'])} exact, "
              f"{len(result['ambiguous_matches'])} ambiguous, {len(result['not_found'])} not found")
        
        return result
        
    except Exception as e:
        result["error"] = f"Error searching colleagues: {str(e)}"
        print(f"❌ [DB] {result['error']}")
        return result


def get_user_calendar_info(user_email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve calendar-related information for a specific user.
    
    Args:
        user_email: The email address of the user
        
    Returns:
        Dictionary with calendar info (name, email, calendar_provider, 
        hashed_access_token, business_hours) or None if not found
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("subscription_services").select(
            "name, email, calendar_provider, hashed_access_token, business_hours"
        ).eq("email", user_email.lower()).eq("activated", True).execute()
        
        if not response.data:
            print(f"❌ [DB] No calendar info found for {user_email}")
            return None
        
        user_data = response.data[0]
        print(f"✅ [DB] Calendar info retrieved for {user_email}")
        
        return {
            "name": user_data.get("name"),
            "email": user_data.get("email"),
            "calendar_provider": user_data.get("calendar_provider"),
            "hashed_access_token": user_data.get("hashed_access_token"),
            "business_hours": user_data.get("business_hours")
        }
        
    except Exception as e:
        print(f"❌ [DB] Error retrieving calendar info for {user_email}: {str(e)}")
        return None


def get_attachments_by_sender_email(target_sender_email: str, user_configured_emails: List[str]) -> Dict[str, Any]:
    """
    Retrieve attachments from emails sent by a specific sender.
    
    This function performs a join between the threads and email_attachments tables
    to find all attachments from a specific sender, restricted to the user's configured mailboxes.
    
    Args:
        target_sender_email: The email address of the sender to search for
        user_configured_emails: List of the user's configured email addresses (for security filtering)
        
    Returns:
        Dictionary with:
        - 'status': 'no_emails' | 'no_attachments' | 'success'
        - 'data': List of attachment dictionaries (empty if no results)
        
        Each attachment dict contains: attachment_id, file_name, file_path, created_at
    """
    result = {
        "status": "no_emails",
        "data": []
    }
    
    if not target_sender_email or not user_configured_emails:
        print(f"❌ [DB] Invalid parameters: target_sender_email={target_sender_email}, user_configured_emails={user_configured_emails}")
        return result
    
    try:
        supabase = get_supabase_client()
        
        # Normalize emails for case-insensitive comparison
        target_email_lower = target_sender_email.lower().strip()
        configured_emails_lower = [e.lower().strip() for e in user_configured_emails]
        
        # Step 1: Query threads table to find threads from this sender
        # Filter by sender_email (or last_sender_email) and ensure box_email is in user's configured emails
        threads_response = supabase.table("threads").select(
            "thread_id"
        ).or_(
            f"sender_email.ilike.{target_email_lower},last_sender_email.ilike.{target_email_lower}"
        ).in_("box_email", configured_emails_lower).execute()
        
        if not threads_response.data:
            # No threads found from this sender
            print(f"ℹ️ [DB] No threads found from sender: {target_sender_email}")
            result["status"] = "no_emails"
            return result
        
        # Extract thread_ids
        thread_ids = [row["thread_id"] for row in threads_response.data]
        print(f"✅ [DB] Found {len(thread_ids)} threads from sender: {target_sender_email}")
        
        # Step 2: Query email_attachments table for these thread_ids
        attachments_response = supabase.table("email_attachments").select(
            "attachment_id, file_name, file_path, created_at"
        ).in_("thread_id", thread_ids).order("created_at", desc=True).execute()
        
        if not attachments_response.data:
            # Threads exist but no attachments
            print(f"ℹ️ [DB] No attachments found for threads from sender: {target_sender_email}")
            result["status"] = "no_attachments"
            return result
        
        # Step 3: Return successful result with attachments
        result["status"] = "success"
        result["data"] = [
            {
                "attachment_id": att.get("attachment_id"),
                "file_name": att.get("file_name"),
                "file_path": att.get("file_path"),
                "created_at": att.get("created_at")
            }
            for att in attachments_response.data
        ]
        
        print(f"✅ [DB] Retrieved {len(result['data'])} attachments from sender: {target_sender_email}")
        return result
        
    except Exception as e:
        print(f"❌ [DB] Error retrieving attachments for sender {target_sender_email}: {str(e)}")
        result["status"] = "no_emails"
        return result