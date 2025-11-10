"""
Core workflow nodes for email processing.
"""

from langgraph.graph import END
from .config import NodeNames
from ..llm.client import llm_client
from ..models.llm_responses import DangerousEmailDetected, LowConfidenceClassification

# Import db_client for user configuration and notifications
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
from db_client import get_user_configuration_sync, get_default_configuration, insert_notification_sync
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
        Next node name: "config_loader"
    """
    print(f"📧 [NEW_MAIL] Starting email processing workflow")
    print(f"   📨 Email body length: {len(state.get('email_body', ''))}")
    print(f"   📎 Attachments: {len(state.get('attachments', []))}")
    
    extracted_info = state.get('extracted_info', {})
    thread_id = extracted_info.get('thread_id', 'unknown')
    from_email = extracted_info.get('from', 'unknown')
    
    print(f"   🧵 Thread ID: {thread_id}")
    print(f"   📤 From: {from_email}")
    
    return NodeNames.CONFIG_LOADER


def config_loader_node(state):
    """
    Loads user configuration from database based on box_email.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with user configuration
    """
    try:
        print(f"⚙️ [CONFIG_LOADER] Loading user configuration...")
        
        # Get box_email from extracted_info
        extracted_info = state.get("extracted_info", {})
        box_email = extracted_info.get("box_email")
        
        if not box_email:
            print(f"⚠️ [CONFIG_LOADER] No box_email found in extracted_info, using default config")
            user_config = get_default_configuration()
        else:
            print(f"🔍 [CONFIG_LOADER] Loading config for box_email: {box_email}")
            
            # Load user configuration from database
            user_config = get_user_configuration_sync(box_email)
            
            if not user_config:
                print(f"⚠️ [CONFIG_LOADER] No config found for {box_email}, using default")
                user_config = get_default_configuration()
        
        # Add user configuration to state
        state["user_config"] = user_config.to_dict()
        
        print(f"✅ [CONFIG_LOADER] Configuration loaded successfully")
        print(f"   📧 User: {user_config.email}")
        print(f"   ✅ Activated: {user_config.activated}")
        print(f"   📊 Thresholds loaded: response={user_config.confidence_response_threshold}, "
              f"review={user_config.confidence_review_mail}, "
              f"priority={user_config.priority_threshold}")
        
        return state
        
    except Exception as e:
        print(f"❌ [CONFIG_LOADER] Error loading user configuration: {e}")
        # Use default configuration on error
        default_config = get_default_configuration()
        state["user_config"] = default_config.to_dict()
        return state


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
            box_email = extracted_info.get("box_email", "unknown")
            
            # Insert notification in database
            try:
                notification_success = insert_notification_sync(
                    email=box_email,
                    notification_type="MAIL_NOT_PERMITTED",
                    message_id=message_id,
                    text=None  # No text as requested
                )
                
                if not notification_success:
                    print(f"❌ [GUARDRAIL] Failed to insert notification for {box_email}")
                    
            except Exception as e:
                print(f"❌ [GUARDRAIL] Error inserting notification: {e}")
            
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
    Classifies the email into categories using LLM with confidence checking.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with classification or LowConfidenceClassification if confidence too low
    """
    try:
        print(f"🏷️ [CLASSIFIER] Starting email classification...")
        
        # Get required data from state
        filtered_body = state.get("email_body", "")
        language = state.get("language", "ITA")
        extracted_info = state.get("extracted_info", {})
        user_config = state.get("user_config", {})
        
        # Get email metadata
        subject = extracted_info.get("subject", "")
        extended_summary = extracted_info.get("extended_summary", "")
        thread_id = extracted_info.get("thread_id", "unknown")
        message_id = extracted_info.get("message_id", "unknown")
        
        # Get confidence threshold from user config
        confidence_threshold = user_config.get("confidence_classification_threshold", 0.75)
        user_email = user_config.get("email", "unknown")
        
        print(f"🎯 [CLASSIFIER] Classification parameters:")
        print(f"   📧 User: {user_email}")
        print(f"   📋 Subject: {subject[:50]}...")
        print(f"   📄 Body length: {len(filtered_body)}")
        print(f"   🔒 Language: {language}")
        print(f"   📊 Confidence threshold: {confidence_threshold}")
        print(f"   📝 Existing summary: {'Yes' if extended_summary else 'No'}")
        
        if not filtered_body or not filtered_body.strip():
            print(f"⚠️ [CLASSIFIER] No filtered body found")
            return state
        
        # Perform email classification using LLM
        classification_response = llm_client.classify_email(
            filtered_body, subject, language, extended_summary
        )
        
        # Check confidence against threshold
        if classification_response.confidence_score >= confidence_threshold:
            print(f"✅ [CLASSIFIER] Classification passed (confidence: {classification_response.confidence_score} >= {confidence_threshold})")
            
            # Update state with successful classification
            state["category"] = classification_response.category
            state["confidence_score"] = classification_response.confidence_score
            state["mail_summary"] = classification_response.mail_summary
            
            # Update extended_summary in extracted_info
            if "extracted_info" not in state:
                state["extracted_info"] = {}
            state["extracted_info"]["extended_summary"] = classification_response.extended_summary
            
            print(f"🏷️ [CLASSIFIER] Email classified successfully:")
            print(f"   📂 Category: {classification_response.category}")
            print(f"   📊 Confidence: {classification_response.confidence_score}")
            print(f"   📝 Summary: {classification_response.mail_summary[:100]}...")
            
            return state
            
        else:
            print(f"⚠️ [CLASSIFIER] LOW CONFIDENCE DETECTED!")
            print(f"   📊 Confidence: {classification_response.confidence_score} < {confidence_threshold}")
            print(f"   🚫 Stopping workflow - human review required")
            
            # Create low confidence classification response
            low_confidence_response = LowConfidenceClassification(
                message_id=message_id,
                thread_id=thread_id,
                message=f"Email classification confidence ({classification_response.confidence_score}) is below threshold ({confidence_threshold}). Human review required.",
                result={
                    "extended_summary": classification_response.extended_summary,
                    "category": classification_response.category,
                    "human_response": True
                }
            )
            
            # Update state to indicate low confidence classification
            state["low_confidence_classification"] = low_confidence_response.dict()
            return state
        
    except Exception as e:
        print(f"❌ [CLASSIFIER] Error in email classification: {e}")
        # Continue with default classification on error
        state["category"] = "OTHER"
        state["confidence_score"] = 0.0
        return state


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
