"""
Core workflow nodes for email processing.
"""

from langgraph.graph import END
from .config import NodeNames
from ..llm.client import llm_client
from ..models.llm_responses import DangerousEmailDetected
""" from .utils import (
    get_email_body,
    get_attachments,
    detect_language,
    validate_content,
    classify_category,
    notify_admin
) """



def new_mail_node(state):
    """
    Receives and prepares email data.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name: "language_detector"
    """
    #state["email_body"] = get_email_body()
    #state["attachments"] = get_attachments()
    return NodeNames.LANGUAGE_DETECTOR


def language_detector_node(state):
    """
    Detects the language of the email using GPT-4o-mini.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with detected language
    """
    try:
        print(f"🔍 [LANGUAGE_DETECTOR] Starting language detection...")
        
        # Get email body from state
        email_body = state.get("email_body", "")
        
        if not email_body or not email_body.strip():
            print(f"⚠️ [LANGUAGE_DETECTOR] No email body found, defaulting to ITA")
            state["language"] = "ITA"
            return state
        
        # Detect language using LLM (first 400 characters)
        language_response = llm_client.detect_language(email_body)
        detected_language = language_response.language
        
        # Update state
        state["language"] = detected_language
        
        print(f"✅ [LANGUAGE_DETECTOR] Language detected: {detected_language}")
        print(f"📝 [LANGUAGE_DETECTOR] Text analyzed: '{email_body[:100]}...'")
        
        return state
        
    except Exception as e:
        print(f"❌ [LANGUAGE_DETECTOR] Error detecting language: {e}")
        # Default to ITA on error
        state["language"] = "ITA"
        return state


def ai_filter_node(state):
    """
    Filters email body removing structural elements and HTML residue.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with filtered email body
    """
    try:
        print(f"🧹 [AI_FILTER] Starting email body filtering...")
        
        # Get email body and language from state
        email_body = state.get("email_body", "")
        language = state.get("language", "ITA")
        
        if not email_body or not email_body.strip():
            print(f"⚠️ [AI_FILTER] No email body found")
            return state
        
        # Filter email body using LLM
        filter_response = llm_client.filter_email_body(email_body, language)
        filtered_body = filter_response.filtered_body
        
        # Update state with filtered body
        state["email_body"] = filtered_body
        
        print(f"✅ [AI_FILTER] Email body filtered successfully")
        print(f"📝 [AI_FILTER] Original: {len(email_body)} chars → Filtered: {len(filtered_body)} chars")
        
        return state
        
    except Exception as e:
        print(f"❌ [AI_FILTER] Error filtering email body: {e}")
        # Continue with original body on error
        return state


def guardrail_node(state):
    """
    Security guardrail to check for scams, phishing, and prompt injection.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state or DangerousEmailDetected if threat detected
    """
    try:
        print(f"🛡️ [GUARDRAIL] Starting security analysis...")
        
        # Get filtered body and language from state
        filtered_body = state.get("email_body", "")
        language = state.get("language", "ITA")
        
        if not filtered_body or not filtered_body.strip():
            print(f"⚠️ [GUARDRAIL] No filtered body found")
            return state
        
        # Perform security check using LLM with salt protection
        security_response = llm_client.check_email_security_protected(filtered_body, language)
        
        # Check if email is safe to process
        if not security_response.permitted or security_response.attempted_scam:
            print(f"🚨 [GUARDRAIL] DANGEROUS EMAIL DETECTED!")
            print(f"   Permitted: {security_response.permitted}")
            print(f"   Attempted Scam: {security_response.attempted_scam}")
            print(f"   Message: {security_response.message_error}")
            
            # Extract thread and message IDs from state
            extracted_info = state.get("extracted_info", {})
            thread_id = extracted_info.get("thread_id", "unknown")
            message_id = extracted_info.get("message_id", "unknown")
            
            # Return dangerous email response
            dangerous_response = DangerousEmailDetected(
                message_id=message_id,
                thread_id=thread_id,
                message=security_response.message_error or "Email contains suspicious or dangerous content",
                attempted_scam=security_response.attempted_scam
            )
            
            # Update state to indicate dangerous email detected
            state["dangerous_email"] = dangerous_response.dict()
            return state
        
        print(f"✅ [GUARDRAIL] Email passed security checks")
        return state
        
    except Exception as e:
        print(f"❌ [GUARDRAIL] Error in security analysis: {e}")
        # Continue processing on error (safe default)
        return state


def ai_filter_guardrail_node(state):
    """
    DEPRECATED: Kept for backward compatibility.
    Use ai_filter_node and guardrail_node separately.
    """
    return NodeNames.CLASSIFIER


def classifier_node(state):
    """
    Classifies the email into categories.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name: "router" or END
    """
    #state["category"] = classify_category(state["email_body"], state["language"])

    return NodeNames.ROUTER


def router_node(state):
    """
    Routes to the appropriate data extraction agent.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name based on category
    """
    category = state["category"]
    
    category_routing = {
        "PROMOTION": "extract_promotion",
        "LOCAL_NOTIFICATION": "extract_local_notification",
        "WEB_PROVIDERS": "extract_web_providers",
        "CALENDAR_EVENTS": "extract_calendar_events",
        "TRANSACTION": "extract_transaction"
    }
    
    return category_routing.get(category, "extract_other") 


def save_and_exit_node(state):
    """
    Final node: saves everything to DB and notifies user.
    
    Args:
        state: Current workflow state
        
    Returns:
        END signal
    """
    ##
    
    return END
