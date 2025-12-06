"""
Core workflow nodes for email processing.
"""

import os
from dotenv import load_dotenv
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv()

from .config import NodeNames
from ..llm.client import llm_client
from db_client import (
    get_calendar_service_data, 
    get_scheduled_event_by_code, 
    delete_event_from_db, 
    get_user_configuration_sync, 
    get_default_configuration, 
    get_email_attachments_sync, 
    get_company_information_sync
) 
from ec_system.utils.utils import delete_google_calendar_event, delete_microsoft_calendar_event
from datetime import datetime

# Import attachment extractor service
from ..services.attachment_extractor import attachment_extractor

# Get max iteration for writer-reviewer loop
MAX_REVIEW_ITERATIONS = int(os.getenv("MAX_REVIEW_ITERATIONS", 3))
CORRECTNESS_THRESHOLD = float(os.getenv("CORRECTNESS_THRESHOLD", 0.9))


def new_mail_node(state):
    """
    Receives and prepares email data.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state
    """
    print(f"📧 [NEW_MAIL] Starting email processing workflow")
    print(f"   📨 Email body length: {len(state.get('email_body', ''))}")
    print(f"   📎 Attachments: {len(state.get('attachments', []))}")
    
    extracted_info = state.get('extracted_info', {})
    thread_id = extracted_info.get('thread_id', 'unknown')
    from_email = extracted_info.get('from', 'unknown')
    
    print(f"   🧵 Thread ID: {thread_id}")
    print(f"   📤 From: {from_email}")
    
    return state


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
        
        state["dangerous_email"] = False
        # Check if email is safe to process
        if not security_response.permitted or security_response.attempted_scam:
            print(f"🚨 [GUARDRAIL] DANGEROUS EMAIL DETECTED!")
            print(f"   Permitted: {security_response.permitted}")
            print(f"   Attempted Scam: {security_response.attempted_scam}")
            print(f"   Message: {security_response.message_error}")
            
            # Update state to indicate dangerous email detected
            state["dangerous_email"] = True
            return state
        
        print(f"✅ [GUARDRAIL] Email passed security checks")
        return state
        
    except Exception as e:
        print(f"❌ [GUARDRAIL] Error in security analysis: {e}")
        # TODO migliorare gestione errori
        return state


def summarizer_node(state):
    """
    Generate summaries for the email (mail_summary and extended_summary).
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with summaries
    """
    try:
        print(f"📝 [SUMMARIZER] Starting email summarization...")
        
        # Get required data from state
        filtered_body = state.get("email_body", "")
        language = state.get("language", "ITA")
        extracted_info = state.get("extracted_info", {})
        
        # Get email metadata
        subject = extracted_info.get("subject", "")
        extended_summary = extracted_info.get("extended_summary", "")
        thread_id = extracted_info.get("thread_id", "unknown")
        
        print(f"📋 [SUMMARIZER] Summarization parameters:")
        print(f"   📋 Subject: {subject[:50]}...")
        print(f"   📄 Body length: {len(filtered_body)}")
        print(f"   🔒 Language: {language}")
        print(f"   📝 Existing summary: {'Yes' if extended_summary else 'No'}")
        print(f"   🧵 Thread ID: {thread_id}")
        
        if not filtered_body or not filtered_body.strip():
            print(f"⚠️ [SUMMARIZER] Empty email body, skipping summarization")
            return state
        
        # Generate email summaries using LLM
        summary_response = llm_client.summarize_email(
            filtered_body, subject, language, extended_summary
        )
        
        # Update state with summaries
        state["mail_summary"] = summary_response.mail_summary
        state["extended_summary"] = summary_response.extended_summary
        
        print(f"✅ [SUMMARIZER] Email summarized successfully")
        print(f"   📝 Mail summary: {len(summary_response.mail_summary)} chars")
        print(f"   📄 Extended summary: {len(summary_response.extended_summary)} chars")
        
        return state
        
    except Exception as e:
        print(f"❌ [SUMMARIZER] Error in email summarization: {e}")
        # Continue with default summaries on error
        state["mail_summary"] = "Summary generation failed"
        if "extended_summary" not in state:
            state["extended_summary"] = "Extended summary generation failed"
        return state


def classifier_node(state):
    """
    Classifies the email into categories using LLM with confidence checking.
    IMPORTANT: Uses only email body and subject - NOT summaries.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with classification or LowConfidenceClassification if confidence too low
    """
    try:
        print(f"🏷️ [CLASSIFIER] Starting email category classification...")
        
        # Get required data from state
        filtered_body = state.get("email_body", "")
        language = state.get("language", "ITA")
        extracted_info = state.get("extracted_info", {})
        user_config = state.get("user_config", {})
        
        # Get email metadata
        subject = extracted_info.get("subject", "")
        thread_id = extracted_info.get("thread_id", "unknown")
        message_id = extracted_info.get("message_id", "unknown")
        has_attachments = extracted_info.get("has_attachments", False)
        
        # Get confidence threshold from user config
        confidence_threshold = user_config.get("confidence_classification_threshold", 0.75)
        user_email = user_config.get("email", "unknown")
        
        print(f"🎯 [CLASSIFIER] Classification parameters:")
        print(f"   📧 User: {user_email}")
        print(f"   📋 Subject: {subject[:50]}...")
        print(f"   📄 Body length: {len(filtered_body)}")
        print(f"   🔒 Language: {language}")
        print(f"   📎 Has attachments: {has_attachments}")
        print(f"   📊 Confidence threshold: {confidence_threshold}")
        print(f"   ⚠️ NOTE: Classification uses ONLY body and subject (no summaries)")
        
        if not filtered_body or not filtered_body.strip():
            print(f"⚠️ [CLASSIFIER] Empty email body, using default classification")
            state["category"] = "OTHER"
            state["confidence_score"] = 0.0
            state["must_see_attachments"] = False
            return state
        
        # Perform email category classification using LLM (NO SUMMARIES)
        classification_response = llm_client.classify_email_category(
            filtered_body, subject, language, has_attachments
        )
        state["low_confidence_classification"] = False

        # Check confidence against threshold
        if classification_response.confidence_score >= confidence_threshold:
            # High confidence - continue to router
            state["category"] = classification_response.category
            state["confidence_score"] = classification_response.confidence_score
            state["must_see_attachments"] = classification_response.must_see_attachments
            
            print(f"✅ [CLASSIFIER] High confidence classification")
            print(f"   🏷️ Category: {classification_response.category}")
            print(f"   📊 Confidence: {classification_response.confidence_score}")
            print(f"   📎 Must see attachments: {classification_response.must_see_attachments}")
            print(f"   🎯 Threshold: {confidence_threshold} (PASSED)")
            print(f"   ✅ Workflow continues to ROUTER")
            
            return state
            
        else:
            # Update state to indicate low confidence classification
            state["category"] = classification_response.category
            state["low_confidence_classification"] = True
            return state
        
    except Exception as e:
        print(f"❌ [CLASSIFIER] Error in email classification: {e}")
        # Continue with default classification on error
        state["category"] = "OTHER"
        state["confidence_score"] = 0.0
        return state


def attachment_extractor_node(state):
    """
    Extract content from email attachments if present.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with attachment contents or unchanged if no attachments
    """
    try:
        print(f"📎 [ATTACHMENT_EXTRACTOR] Starting attachment content extraction...")
        
        # Get attachments from state
        attachments = state.get("attachments", [])
        extracted_info = state.get("extracted_info", {})
        
        print(f"📎 [ATTACHMENT_EXTRACTOR] Found {len(attachments)} attachment IDs")
        
        # Check if there are attachments to process
        if not attachments or len(attachments) == 0:
            print(f"📎 [ATTACHMENT_EXTRACTOR] No attachments to process, continuing to router")
            state["attachment_contents"] = []
            return state
        
        # Get thread_id and message_id for database queries
        thread_id = extracted_info.get("thread_id")
        message_id = extracted_info.get("message_id")
        
        print(f"📎 [ATTACHMENT_EXTRACTOR] Processing attachments for thread: {thread_id}, message: {message_id}")
        
        if not thread_id or not message_id:
            print(f"❌ [ATTACHMENT_EXTRACTOR] Missing thread_id or message_id")
            state["attachment_contents"] = []
            return state
        
        # Query database for attachment file paths using db_client
        attachment_files = []
        
        try:
            # Get attachment files from database using db_client
            attachment_files = get_email_attachments_sync(message_id)
                
        except Exception as e:
            print(f"❌ [ATTACHMENT_EXTRACTOR] Database query error: {e}")
            state["attachment_contents"] = []
            return state
        
        # Check file sizes before processing
        if attachment_files:
            # Get size limit from environment (in KB, default 2048 KB = 2MB)
            max_size_kb = int(os.getenv("MAX_ATTACHMENT_SIZE_KB", "2048"))
            max_size_bytes = max_size_kb * 1024  # Convert to bytes
            
            print(f"📎 [ATTACHMENT_EXTRACTOR] Checking file sizes (limit: {max_size_kb} KB)")
            
            files_too_large = []
            processable_files = []
            
            for attachment_file in attachment_files:
                file_name = attachment_file.get("file_name", "unknown")
                file_size = attachment_file.get("size_bytes", 0)
                file_size_kb = file_size / 1024
                
                if file_size > max_size_bytes:
                    files_too_large.append({
                        "file_name": file_name,
                        "size_kb": round(file_size_kb, 2)
                    })
                    print(f"⚠️ [ATTACHMENT_EXTRACTOR] File too large: {file_name} ({file_size_kb:.2f} KB > {max_size_kb} KB)")
                else:
                    processable_files.append(attachment_file)
                    print(f"✅ [ATTACHMENT_EXTRACTOR] File size OK: {file_name} ({file_size_kb:.2f} KB)")
            
            # Update state if any files are too large
            if files_too_large:
                state["attachments_too_large"] = True
                print(f"🚨 [ATTACHMENT_EXTRACTOR] {len(files_too_large)} files exceed size limit, skipping extraction")
                print(f"📋 [ATTACHMENT_EXTRACTOR] Large files: {[f['file_name'] for f in files_too_large]}")
                state["attachment_contents"] = []
                return state
            else:
                state["attachments_too_large"] = False
                attachment_files = processable_files
        
        # Extract content from attachment files
        if attachment_files:
            extracted_contents = attachment_extractor.extract_attachments_content(attachment_files)
            state["attachment_contents"] = extracted_contents
            
            print(f"✅ [ATTACHMENT_EXTRACTOR] Successfully extracted content from {len(extracted_contents)} attachments")
            
            # CONSOLE OUTPUT: Detailed summary of all extracted contents
            print(f"")
            print(f"🗂️ [ATTACHMENT_SUMMARY] COMPLETE EXTRACTION RESULTS:")
            print(f"=" * 80)
            
            if extracted_contents:
                for idx, content in enumerate(extracted_contents, 1):
                    file_name = content.get('nome_file', 'unknown')
                    file_content = content.get('contenuto', '')
                    content_length = len(str(file_content))
                    
                    print(f"📁 ATTACHMENT {idx}: {file_name}")
                    print(f"   📊 Content Length: {content_length} characters")
                    print(f"   📝 Content Summary:")
                    print(f"   " + "-" * 50)
                    
                    # Show content preview
                    content_preview = str(file_content)[:800]  # Show more for console
                    for line_num, line in enumerate(content_preview.split('\n'), 1):
                        if line_num <= 20:  # Show first 20 lines
                            print(f"   {line_num:2d}| {line}")
                        else:
                            break
                    
                    if len(str(file_content)) > 800 or len(content_preview.split('\n')) > 20:
                        total_lines = len(str(file_content).split('\n'))
                        print(f"   ... [showing first 20 lines of {total_lines} total lines]")
                    
                    print(f"   " + "-" * 50)
                    print()
                
                # JSON-formatted output for easy parsing
                print(f"📋 [JSON_OUTPUT] Extracted Contents:")
                print(f"{'-' * 40}")
                import json
                try:
                    json_output = json.dumps(extracted_contents, indent=2, ensure_ascii=False)
                    print(json_output)
                except Exception as e:
                    print(f"❌ JSON serialization error: {e}")
                    print(f"Raw contents: {extracted_contents}")
                print(f"{'-' * 40}")
            else:
                print(f"⚠️ No content was extracted from any attachments")
            
            print(f"=" * 80)
            print()
            
        else:
            print(f"⚠️ [ATTACHMENT_EXTRACTOR] No attachment files found to process")
            state["attachment_contents"] = []
        
        return state
        
    except Exception as e:
        print(f"❌ [ATTACHMENT_EXTRACTOR] Error in attachment extraction: {e}")
        # Continue with empty attachment contents on error
        state["attachment_contents"] = []
        return state


def router_node(state):
    """
    Routes to the appropriate data extraction agent.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state (routing handled by conditional edges in graph)
    """
    category = state.get("category", "OTHER")
    
    print(f"🔀 [ROUTER] Routing email based on category: {category}")
    print(f"   🏷️ Category: {category}")
    print(f"   📊 Confidence: {state.get('confidence_score', 'Not set')}")
    print(f"   📝 Mail Summary: {state.get('mail_summary', 'Not set')[:50]}...")
    
    # For now, just return the state - routing logic will be in conditional edges
    # This is a placeholder until specific extraction nodes are implemented
    print(f"   ⚠️ [ROUTER] Extraction nodes not yet implemented - ending workflow")
    
    return state 


def attachment_summarizer_node(state):
    """
    Generate a discursive summary of all attachment contents.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with attachment summary
    """
    try:
        print(f"📋 [ATTACHMENT_SUMMARIZER] Starting attachment content summarization...")
        
        # Get required data from state
        attachment_contents = state.get("attachment_contents", [])
        language = state.get("language", "ITA")
        
        if not attachment_contents or len(attachment_contents) == 0:
            print(f"⚠️ [ATTACHMENT_SUMMARIZER] No attachment contents to summarize")
            state["summary_attachments"] = None
            return state
        
        print(f"📎 [ATTACHMENT_SUMMARIZER] Summarizing {len(attachment_contents)} attachment(s)")
        print(f"🔒 [ATTACHMENT_SUMMARIZER] Language: {language}")
        
        # Generate attachment summary using LLM
        summary_response = llm_client.summarize_attachments(
            attachment_contents, language
        )
        
        # Update state with summary
        state["summary_attachments"] = summary_response.summary_attachments
        
        print(f"✅ [ATTACHMENT_SUMMARIZER] Attachment summary generated successfully")
        print(f"📝 [ATTACHMENT_SUMMARIZER] Summary length: {len(summary_response.summary_attachments)} chars")
        
        return state
        
    except Exception as e:
        print(f"❌ [ATTACHMENT_SUMMARIZER] Error in attachment summarization: {e}")
        # Continue with no summary on error
        state["summary_attachments"] = None
        return state


def evaluator_node(state):
    """
    Evaluate email with category-specific priority scoring and subcategory classification.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with priority_score and subcategory
    """
    try:
        print(f"📊 [EVALUATOR] Starting category-specific email evaluation...")
        
        # Get required data from state
        category = state.get("category", "OTHER")
        language = state.get("language", "ITA")
        
        # Get email data
        extracted_info = state.get("extracted_info", {})
        subject = extracted_info.get("subject", "")
        filtered_body = state.get("email_body", "")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        print(f"🎯 [EVALUATOR] Evaluation parameters:")
        print(f"   🏷️ Category: {category}")
        print(f"   🔒 Language: {language}")
        print(f"   📋 Subject: {subject[:50]}...")
        print(f"   📄 Body length: {len(filtered_body)} chars")
        print(f"   📝 Mail summary: {len(mail_summary)} chars")
        print(f"   📎 Attachment summary: {len(summary_attachments) if summary_attachments else 0} chars")
        
        # Validate required fields
        if not category or not filtered_body or not mail_summary:
            print(f"⚠️ [EVALUATOR] Missing required fields, using default evaluation")
            state["priority_score"] = 0.5
            state["subcategory"] = "GENERICO"
            return state
        
        # Evaluate email using category-specific LLM evaluation
        evaluation_response = llm_client.evaluate_email(
            category=category,
            subject=subject,
            filtered_body=filtered_body,
            mail_summary=mail_summary,
            summary_attachments=summary_attachments or "",
            language=language
        )

        if evaluation_response is None:
            # Update state to indicate low confidence classification
            state["low_confidence_classification"] = True
            return state
        
        # Update state with evaluation results
        state["priority_score"] = evaluation_response.priority_score
        state["subcategory"] = evaluation_response.subcategory
        state["low_confidence_classification"] = False
        
        print(f"✅ [EVALUATOR] Email evaluation completed successfully")
        print(f"   📊 Priority Score: {evaluation_response.priority_score}")
        print(f"   🏷️ Subcategory: {evaluation_response.subcategory}")
        print(f"   🎯 Category: {category}")
        
        return state
        
    except Exception as e:
        print(f"❌ [EVALUATOR] Error in email evaluation: {e}")
        # Continue with default evaluation on error
        state["priority_score"] = 0.5
        state["subcategory"] = "GENERICO"
        return state


def priority_controller_node(state):
    """
    Controls email priority based on user's priority threshold.
    If priority_score >= threshold, end workflow (high priority).
    Otherwise, continue to subcategory routing.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with routing decision
    """
    try:
        print(f"🎯 [PRIORITY_CONTROLLER] Checking priority threshold...")
        
        # Get priority data from state
        priority_score = state.get("priority_score", 0.0)
        user_config = state.get("user_config", {})
        subcategory = state.get("subcategory", "SPAM_OR_UNKNOWN")
        
        # Get priority threshold from user config
        priority_threshold = user_config.get("priority_threshold", 0.6)
        user_email = user_config.get("email", "unknown")
        
        print(f"📊 [PRIORITY_CONTROLLER] Priority analysis:")
        print(f"   👤 User: {user_email}")
        print(f"   🔥 Priority score: {priority_score}")
        print(f"   🏷️ Subcategory: {subcategory}")
        
        # Determine routing based on priority
        if priority_score >= priority_threshold:            
            # Mark for high priority handling
            print(f"🔥 [PRIORITY_CONTROLLER] HIGH PRIORITY - Score {priority_score} >= threshold {priority_threshold}")
            state["high_priority_email"] = True
            return state
        else:
            print(f"📋 [PRIORITY_CONTROLLER] Normal priority - Routing to subcategory handler")
            state["high_priority_email"] = False
            # Continue to subcategory routing
            return state
            
    except Exception as e:
        # TODO Send notification and save to database
        print(f"❌ [PRIORITY_CONTROLLER] Error in priority control: {e}")
        return state


# SUBCATEGORY HANDLER NODES
def handle_offer_promotion_node(state):
    """Handle OFFER_PROMOTION subcategory emails - automated processing."""
    print(f"🎯 [OFFER_PROMOTION] Processing promotional offer email (automated)")
    state["automation_executed"] = True
    return state


def handle_newsletter_node(state):
    """Handle NEWSLETTER subcategory emails - automated processing."""
    print(f"📰 [NEWSLETTER] Processing newsletter email (automated)")
    state["automation_executed"] = True
    return state


def handle_event_invite_node(state):
    """Handle EVENT_INVITE subcategory emails - conditional processing."""
    print(f"🎉 [EVENT_INVITE] Processing event invitation email")
    
    category = state.get("category")
    
    # If category is promotion or social_notification, automate
    if category in ["PROMOTION", "SOCIAL_NOTIFICATION"]:
        state["automation_executed"] = True
        return state

    else:
        state["human_response"] = True
        state["automation_executed"] = True
        state["status"] = "EVENT_INVITE_HUMAN_RESPONSE_REQUIRED"
        return state


def handle_product_update_node(state):
    """Handle PRODUCT_UPDATE subcategory emails - conditional processing."""
    print(f"📦 [PRODUCT_UPDATE] Processing product update email")
    
    category = state.get("category")
    
    # If category is promotion, automate
    if category == "PROMOTION":
        state["automation_executed"] = True
        return state
    else:
        return state


def handle_request_quote_node(state):
    """Handle REQUEST_QUOTE subcategory emails."""
    print(f"💰 [REQUEST_QUOTE] Processing quote request email")
    #TODO andrebbe controllato response_to_quote

    category = state.get("category")

    if category == "INFO_REQUESTED":
        state["human_response"] = True
    state["automation_executed"] = True

    return state


def handle_new_message_node(state):
    """Handle NEW_MESSAGE subcategory emails - automated processing."""
    print(f"💬 [NEW_MESSAGE] Processing new message notification (automated)")
    state["automation_executed"] = True
    return state

def handle_connection_request_node(state):
    """Handle CONNECTION_REQUEST subcategory emails - conditional processing."""
    print(f"🤝 [CONNECTION_REQUEST] Processing connection request")
    
    category = state.get("category")
    
    # If category is social_notification, automate
    if category == "SOCIAL_NOTIFICATION":
        state["automation_executed"] = True
        return state
    else:
        return state


def handle_system_alert_node(state):
    """Handle SYSTEM_ALERT subcategory emails - automated processing."""
    print(f"⚠️ [SYSTEM_ALERT] Processing system alert (automated)")
    state["automation_executed"] = True
    return state


def handle_system_notification_node(state):
    """Handle SYSTEM_NOTIFICATION subcategory emails - automated processing."""
    print(f"🔔 [SYSTEM_NOTIFICATION] Processing system notification (automated)")
    state["automation_executed"] = True
    return state


def handle_sent_documents_node(state):
    """Handle SENT_DOCUMENTS subcategory emails - conditional processing."""
    print(f"📄 [SENT_DOCUMENTS] Processing document delivery notification")
    
    category = state.get("category")
    
    # If category is transactional, automate
    if category == "TRANSACTIONAL":
        state["automation_executed"] = True
        return state
    else:
        return state


def handle_provide_update_node(state):
    """Handle PROVIDE_UPDATE subcategory emails - conditional processing."""
    print(f"📈 [PROVIDE_UPDATE] Processing status update")
    
    category = state.get("category")
    
    # If category is transactional, automate
    if category == "TRANSACTIONAL":
        state["automation_executed"] = True
        return state
    else:
        return state


def handle_confirm_appointment_node(state):
    """Handle CONFIRM_APPOINTMENT subcategory emails."""
    print(f"✅ [CONFIRM_APPOINTMENT] Processing appointment confirmation")
    extracted_info = state.get("extracted_info", {})
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    # TODO: Implement specific logic for appointment confirmations
    return state


def handle_forward_info_node(state):
    """Handle FORWARD_INFO subcategory emails."""
    print(f"↗️ [FORWARD_INFO] Processing information forwarding")
    extracted_info = state.get("extracted_info", {})
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    # TODO: Implement specific logic for information forwarding
    return state


def handle_response_to_request_node(state):
    """Handle RESPONSE_TO_REQUEST subcategory emails."""
    print(f"↩️ [RESPONSE_TO_REQUEST] Processing response to request")
    extracted_info = state.get("extracted_info", {})
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    # TODO: Implement specific logic for responses to requests
    return state


def handle_request_document_node(state):
    """Handle REQUEST_DOCUMENT subcategory emails."""
    print(f"📋 [REQUEST_DOCUMENT] Processing document request")
    
    # TODO ci sarebbe da controllare la configurazione "send_document"
    state["human_response"] = True
    state["automation_executed"] = True

    return state


def handle_event_followup_node(state):
    """Handle EVENT_FOLLOWUP subcategory emails."""
    print(f"🔄 [EVENT_FOLLOWUP] Processing event follow-up")
    return state


def handle_invoice_or_receipt_node(state):
    """Handle INVOICE_OR_RECEIPT subcategory emails - conditional processing."""
    print(f"🧾 [INVOICE_OR_RECEIPT] Processing invoice or receipt")
    
    category = state.get("category")
    
    # If category is transactional, automate
    if category == "TRANSACTIONAL":
        state["automation_executed"] = True
        return state
    else:
        return state


def handle_status_notification_node(state):
    """Handle STATUS_NOTIFICATION subcategory emails - conditional processing."""
    print(f"📊 [STATUS_NOTIFICATION] Processing status notification")
    
    category = state.get("category")
    
    # If category is transactional, automate
    if category == "TRANSACTIONAL":
        state["automation_executed"] = True
        return state
    else:
        return state


def handle_ticket_update_node(state):
    """Handle TICKET_UPDATE subcategory emails - conditional processing."""
    print(f"🎫 [TICKET_UPDATE] Processing ticket update")
    
    category = state.get("category")
    
    if category == "TRANSACTIONAL":
        state["automation_executed"] = True
    return state


def handle_general_greeting_node(state):
    """Handle GENERAL_GREETING subcategory emails."""
    print(f"👋 [GENERAL_GREETING] Processing general greeting")
    return state


def handle_request_appointment_node(state):
    """Handle REQUEST_APPOINTMENT subcategory emails."""
    print(f"📅 [REQUEST_APPOINTMENT] Processing appointment request")
    return state


def handle_request_appointment_change_node(state):
    """Handle REQUEST_APPOINTMENT_CHANGE subcategory emails."""
    print(f"🔄 [REQUEST_APPOINTMENT_CHANGE] Processing appointment change request")
    return state


def handle_request_status_update_node(state):
    """Handle REQUEST_STATUS_UPDATE subcategory emails - conditional processing."""
    print(f"📊 [REQUEST_STATUS_UPDATE] Processing status update request")
    
    category = state.get("category")
    
    # If category is transactional, automate
    if category == "TRANSACTIONAL":
        state["automation_executed"] = True
        return state
    else:
        return state


def handle_ask_for_help_node(state):
    """Handle ASK_FOR_HELP subcategory emails - conditional processing."""
    print(f"🆘 [ASK_FOR_HELP] Processing help request")
    
    category = state.get("category")
    
    if category == "TRANSACTIONAL":
        state["automation_executed"] = True
    return state


def handle_general_inquiry_node(state):
    """Handle GENERAL_INQUIRY subcategory emails."""
    print(f"❓ [GENERAL_INQUIRY] Processing general inquiry")
    return state


def handle_payment_issue_node(state):
    """Handle PAYMENT_ISSUE subcategory emails - conditional processing."""
    print(f"💳 [PAYMENT_ISSUE] Processing payment issue")

    category = state.get("category")
    
    if category == "INFO_REQUESTED":
        state["human_response"] = True

    state["automation_executed"] = True
    return state

def handle_cancel_appointment_node(state):
    """Handle CANCEL_APPOINTMENT subcategory emails."""
    print(f"❌ [CANCEL_APPOINTMENT] Processing appointment cancellation")
    return state
    
def handle_order_confirmation_node(state):
    """Handle ORDER_CONFIRMATION subcategory emails - automated processing."""
    print(f"🛒 [ORDER_CONFIRMATION] Processing order confirmation (automated)")
    state["automation_executed"] = True
    return state


def handle_account_verification_node(state):
    """Handle ACCOUNT_VERIFICATION subcategory emails - automated processing."""
    print(f"🔐 [ACCOUNT_VERIFICATION] Processing account verification (automated)")
    state["automation_executed"] = True
    return state


def handle_internal_note_node(state):
    """Handle INTERNAL_NOTE subcategory emails - automated processing."""
    print(f"📝 [INTERNAL_NOTE] Processing internal note (automated)")
    state["automation_executed"] = True
    return state


def handle_spam_or_unknown_node(state):
    """Handle SPAM_OR_UNKNOWN subcategory emails - automated processing."""
    print(f"🚫 [SPAM_OR_UNKNOWN] Processing spam or unknown content (automated)")
    state["automation_executed"] = True
    return state


def handle_unrelated_content_node(state):
    """Handle UNRELATED_CONTENT subcategory emails - automated processing."""
    print(f"🔀 [UNRELATED_CONTENT] Processing unrelated content (automated)")
    state["automation_executed"] = True
    return state


def subcategory_router_node(state):
    """Router node for subcategory-specific handling."""
    return state


def reader_node(state):
    """
    Extract key entities and determine if email needs response using LLM.
    For REQUEST_APPOINTMENT subcategory, also extracts appointment-specific details.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with key_entities and needs_response (and appointment details if REQUEST_APPOINTMENT)
    """
    try:
        print(f"📖 [READER] Starting email content analysis...")
        
        # Get required data from state
        filtered_body = state.get("email_body", "")
        summary_attachments = state.get("summary_attachments")
        language = state.get("language", "ITA")
        subcategory = state.get("subcategory", "")
        
        print(f"📋 [READER] Analysis parameters:")
        print(f"   📄 Body length: {len(filtered_body)} chars")
        print(f"   📎 Attachments summary: {'Yes' if summary_attachments else 'No'}")
        print(f"   🔒 Language: {language}")
        print(f"   🏷️ Subcategory: {subcategory}")
        
        if not filtered_body or not filtered_body.strip():
            print(f"⚠️ [READER] Empty email body, using default analysis")
            state["key_entities"] = {
                "dates": [],
                "locations": [],
                "people": [],
                "organizations": [],
                "requests": [],
                "actions": [],
                "amounts": [],
                "documents": [],
                "other_info": []
            }
            state["needs_response"] = False
            return state
        
        # Check if this is a REQUEST_APPOINTMENT email
        if subcategory == "REQUEST_APPOINTMENT":
            print(f"📅 [READER] Detected REQUEST_APPOINTMENT - using appointment-specific analysis")
            
            # Get additional data for appointment analysis
            extended_summary = state.get("extended_summary", "")
            extracted_info = state.get("extracted_info", {})
            sender_email = extracted_info.get("from", "mail not available")
            now = datetime.now()
            current_timestamp = f"{now.strftime('%A')}, {now.isoformat()}"
            
            # Analyze appointment request using specialized LLM method
            appointment_response = llm_client.read_appointment_request(
                filtered_body,
                extended_summary,
                current_timestamp,
                sender_email,
                language
            )
            
            # Update state with appointment details
            state["key_entities"] = appointment_response.key_entities
            state["appointment_title"] = appointment_response.title_of_event
            state["appointment_date"] = appointment_response.date
            state["appointment_duration"] = appointment_response.duration
            state["appointment_attendees"] = appointment_response.attendees
            state["appointment_place"] = appointment_response.place
            state["appointment_notes"] = appointment_response.additional_notes
            # REQUEST_APPOINTMENT always needs manual handling, so needs_response is not used
            # but we set it to None for clarity
            state["needs_response"] = None
            
            print(f"✅ [READER] Appointment analysis completed successfully")
            print(f"   📅 Title: {appointment_response.title_of_event}")
            print(f"   🕐 Date: {appointment_response.date}")
            print(f"   ⏱️ Duration: {appointment_response.duration} minutes")
            print(f"   👥 Attendees: {appointment_response.attendees}")
            print(f"   📍 Place: {appointment_response.place}")
            print(f"   📝 Notes: {appointment_response.additional_notes}")
            
        # Check if this is a REQUEST_APPOINTMENT_CHANGE email
        elif subcategory == "REQUEST_APPOINTMENT_CHANGE":
            print(f"🔄 [READER] Detected REQUEST_APPOINTMENT_CHANGE - using appointment change analysis")
            
            # Get additional data for appointment change analysis
            extended_summary = state.get("extended_summary", "")
            mail_summary = state.get("mail_summary", "")
            extracted_info = state.get("extracted_info", {})
            sender_email = extracted_info.get("from", "mail not available")
            now = datetime.now()
            current_timestamp = f"{now.strftime('%A')}, {now.isoformat()}"
            
            # Analyze appointment change request using specialized LLM method
            change_response = llm_client.read_appointment_change_request(
                filtered_body,
                mail_summary,
                extended_summary,
                current_timestamp,
                sender_email,
                language
            )
            
            # Update state with appointment change details
            state["key_entities"] = change_response.key_entities
            state["change_event_code"] = change_response.event_code
            state["change_new_title"] = change_response.new_title_of_event
            state["change_new_date"] = change_response.new_date
            state["change_new_duration"] = change_response.new_duration
            state["change_new_attendees"] = change_response.new_attendees
            state["change_new_place"] = change_response.new_place
            state["change_additional_notes"] = change_response.additional_notes
            # REQUEST_APPOINTMENT_CHANGE needs_response is not used
            state["needs_response"] = None
            
            print(f"✅ [READER] Appointment change analysis completed successfully")
            print(f"   🔑 Event code: {change_response.event_code}")
            print(f"   📅 New title: {change_response.new_title_of_event}")
            print(f"   🕐 New date: {change_response.new_date}")
            print(f"   ⏱️ New duration: {change_response.new_duration} minutes")
            print(f"   👥 New attendees: {change_response.new_attendees}")
            print(f"   📍 New place: {change_response.new_place}")
            print(f"   📝 Notes: {change_response.additional_notes}")
            
        # Check if this is a CANCEL_APPOINTMENT email
        elif subcategory == "CANCEL_APPOINTMENT":
            print(f"❌ [READER] Detected CANCEL_APPOINTMENT - using cancellation analysis")
            
            # Get additional data for cancellation analysis
            extended_summary = state.get("extended_summary", "")
            mail_summary = state.get("mail_summary", "")
            extracted_info = state.get("extracted_info", {})
            sender_email = extracted_info.get("from", "mail not available")
            now = datetime.now()
            current_timestamp = f"{now.strftime('%A')}, {now.isoformat()}"
            
            # Analyze cancellation request using specialized LLM method
            cancellation_response = llm_client.read_cancellation_request(
                filtered_body,
                mail_summary,
                extended_summary,
                current_timestamp,
                sender_email,
                language
            )
            
            # Update state with cancellation details
            state["key_entities"] = cancellation_response.key_entities
            state["cancellation_event_code"] = cancellation_response.event_code
            
            print(f"✅ [READER] Cancellation analysis completed successfully")
            print(f"   🔑 Event code: {cancellation_response.event_code}")
        
        # Check if this is a CONFIRM_APPOINTMENT email
        elif subcategory == "CONFIRM_APPOINTMENT":
            print(f"✅ [READER] Detected CONFIRM_APPOINTMENT - using confirm appointment analysis")
            
            # Get additional data for confirm appointment analysis
            extended_summary = state.get("extended_summary", "")
            extracted_info = state.get("extracted_info", {})
            sender_email = extracted_info.get("from", "mail not available")
            now = datetime.now()
            current_timestamp = f"{now.strftime('%A')}, {now.isoformat()}"
            
            # Analyze confirm appointment using specialized LLM method
            confirm_response = llm_client.read_confirm_appointment(
                filtered_body,
                extended_summary,
                current_timestamp,
                sender_email,
                language
            )
            
            # Update state with confirm appointment details
            state["key_entities"] = confirm_response.key_entities
            state["appointment_title"] = confirm_response.title_of_event
            state["appointment_date"] = confirm_response.date
            state["appointment_duration"] = confirm_response.duration
            state["appointment_attendees"] = confirm_response.attendees
            state["appointment_place"] = confirm_response.place
            state["appointment_notes"] = confirm_response.additional_notes
            state["already_scheduled"] = confirm_response.already_scheduled
            state["confirm_event_code"] = confirm_response.event_code
            state["needs_response"] = confirm_response.needs_response
            
            print(f"✅ [READER] Confirm appointment analysis completed successfully")
            print(f"   📅 Title: {confirm_response.title_of_event}")
            print(f"   🕐 Date: {confirm_response.date}")
            print(f"   ⏱️ Duration: {confirm_response.duration} minutes")
            print(f"   👥 Attendees: {confirm_response.attendees}")
            print(f"   📍 Place: {confirm_response.place}")
            print(f"   📝 Notes: {confirm_response.additional_notes}")
            print(f"   📆 Already Scheduled: {confirm_response.already_scheduled}")
            print(f"   🔑 Event Code: {confirm_response.event_code}")
            print(f"   💬 Needs Response: {confirm_response.needs_response}")
            
        else:
            # Standard email analysis for non-appointment emails
            reader_response = llm_client.read_email(
                filtered_body, 
                summary_attachments or "", 
                language
            )
            
            # Update state with analysis results
            state["key_entities"] = reader_response.key_entities
            state["needs_response"] = reader_response.needs_response
            
            print(f"✅ [READER] Email analysis completed successfully")
            print(f"   📊 Entities extracted: {len(reader_response.key_entities)} categories")
            print(f"   💬 Needs response: {reader_response.needs_response}")
        
        return state
        
    except Exception as e:
        print(f"❌ [READER] Error in email analysis: {e}")

        # TODO return error, notification and save to db

        # Continue with default values on error
        state["key_entities"] = {
            "dates": [],
            "locations": [],
            "people": [],
            "organizations": [],
            "requests": [],
            "actions": [],
            "amounts": [],
            "documents": [],
            "other_info": []
        }
        state["needs_response"] = True  # Default to True to be safe
        return state


def scheduler_node(state):
    """
    Schedule appointments for REQUEST_APPOINTMENT subcategory.
    Uses LLM with tool functions to either book appointment or propose new slots.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with scheduling results
    """
    try:
        print(f"📅 [SCHEDULER] Starting appointment scheduling...")
        
        # Get required data from state
        language = state.get("language", "ITA")
        mail_summary = state.get("mail_summary", "")
        extended_summary = state.get("extended_summary", "")
        appointment_date = state.get("appointment_date")
        
        # Get user config and extracted info for additional parameters
        user_config = state.get("user_config", {})
        extracted_info = state.get("extracted_info", {})
        service_id = user_config.get("service_id")
        thread_id = extracted_info.get("thread_id")
        created_by = extracted_info.get("from", "unknown")
        event_type = "APPOINTMENT"  # Default event type
        
        # Determine if we need to propose slots or book directly
        # If date contains T--:-- it means only day preference without specific time
        propose_slots = False
        if appointment_date is None:
            propose_slots = True
        else:
            try:
                if isinstance(appointment_date, str) and 'T' in appointment_date:
                    time_part = appointment_date.split('T', 1)[1]
                    # Check for day preference format (--:--) which indicates no specific time
                    propose_slots = time_part.startswith('--:--')
                else:
                    propose_slots = False
            except Exception:
                propose_slots = False
        
        print(f"📋 [SCHEDULER] Scheduling parameters:")
        print(f"   🔒 Language: {language}")
        print(f"   🎯 Propose slots: {propose_slots}")
        print(f"   📅 Appointment date: {appointment_date}")
        print(f"   🔑 Service ID: {service_id}")
        print(f"   👤 Created by: {created_by}")
        
        # Get current timestamp with day of week
        now = datetime.now()
        current_timestamp = f"{now.strftime('%A')}, {now.isoformat()}"
        
        # Get appointment details from state (for booking)
        appointment_info = {
            "title_of_event": state.get("appointment_title"),
            "date": state.get("appointment_date"),
            "duration": state.get("appointment_duration", 60),
            "attendees": state.get("appointment_attendees"),
            "place": state.get("appointment_place"),
            "additional_notes": state.get("appointment_notes")
        }
        
        # Extract favorite_day from appointment_date if available (only date part, not time)
        # This avoids LLM miscalculating relative dates like "lunedì prossimo"
        favorite_day = None
        if appointment_date and isinstance(appointment_date, str) and 'T' in appointment_date:
            favorite_day = appointment_date.split('T')[0]  # Extract YYYY-MM-DD
            print(f"📅 [SCHEDULER] Pre-extracted favorite_day from reader: {favorite_day}")
        
        # Call LLM scheduler with tool functions
        scheduler_response = llm_client.schedule_appointment(
            current_timestamp=current_timestamp,
            mail_summary=mail_summary,
            extended_summary=extended_summary,
            propose_slots=propose_slots,
            appointment_info=appointment_info,
            service_id=service_id,
            event_type=event_type,
            created_by=created_by,
            thread_id=thread_id,
            language=language,
            favorite_day=favorite_day
        )
        
        # Update state with scheduling results
        state["appointment_scheduled"] = scheduler_response.scheduled
        state["appointment_overlap"] = scheduler_response.overlap
        state["appointment_event_code"] = scheduler_response.event_code
        state["appointment_proposed_slots"] = scheduler_response.proposed_slots
        state["appointment_favorite_day_unavailable"] = scheduler_response.favorite_day_unavailable
        state["scheduled_event_details"] = scheduler_response.event_details
        
        print(f"✅ [SCHEDULER] Scheduling completed successfully")
        print(f"   ✓ Scheduled: {scheduler_response.scheduled}")
        print(f"   ⚠️ Overlap: {scheduler_response.overlap}")
        print(f"   🔢 Event code: {scheduler_response.event_code}")
        print(f"   📆 Proposed slots: {scheduler_response.proposed_slots}")
        print(f"   📅 Favorite day unavailable: {scheduler_response.favorite_day_unavailable}")
        print(f"   📋 Event details: {'Yes' if scheduler_response.event_details else 'No'}")
        
        return state
        
    except Exception as e:
        print(f"❌ [SCHEDULER] Error in appointment scheduling: {e}")
        # Set default values on error
        state["appointment_scheduled"] = False
        state["appointment_overlap"] = False
        state["appointment_event_code"] = None
        state["appointment_proposed_slots"] = None
        state["appointment_favorite_day_unavailable"] = False
        return state


def rescheduler_node(state):
    """
    Reschedule appointments for REQUEST_APPOINTMENT_CHANGE subcategory.
    First validates event_code, then uses LLM with tool functions to either reschedule appointment or propose new slots.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with rescheduling results or AutomationExecutedResponse if event_code invalid
    """
    try:
        print(f"📅 [RESCHEDULER] Starting appointment rescheduling...")
        
        # Get event_code from state
        event_code = state.get("change_event_code")
        
        # Validate event_code
        if event_code is None or (isinstance(event_code, str) and len(event_code) != 6):
            print(f"⚠️ [RESCHEDULER] Invalid event_code: {event_code}")
            state["status"] = "EVENT_CODE_INVALID"
            return state

        event_response = get_scheduled_event_by_code(event_code)
            
        if not event_response:
            state["status"] = "EVENT_CODE_NOT_FOUND"
            state["human_response"] = True
            state["automation_executed"] = True
            return state


        state["status"] = "EVENT_CODE_VALID"
        
        # Event code is valid, proceed with LLM rescheduling
        print(f"✅ [RESCHEDULER] Valid event_code: {event_code}")
        
        # Get required data from state
        language = state.get("language", "ITA")
        mail_summary = state.get("mail_summary", "")
        extended_summary = state.get("extended_summary", "")
        new_date = state.get("change_new_date")
        
        # Get user config and extracted info for additional parameters
        user_config = state.get("user_config", {})
        extracted_info = state.get("extracted_info", {})
        service_id = user_config.get("service_id")
        thread_id = extracted_info.get("thread_id")
        
        # Determine if we need to propose slots or reschedule directly
        # If date contains T--:-- it means only day preference without specific time
        propose_slots = False
        if new_date is None:
            propose_slots = True
        else:
            try:
                if isinstance(new_date, str) and 'T' in new_date:
                    time_part = new_date.split('T', 1)[1]
                    # Check for day preference format (--:--) which indicates no specific time
                    propose_slots = time_part.startswith('--:--')
                else:
                    propose_slots = False
            except Exception:
                propose_slots = False
        
        print(f"📋 [RESCHEDULER] Rescheduling parameters:")
        print(f"   🔒 Language: {language}")
        print(f"   🎯 Propose slots: {propose_slots}")
        print(f"   📅 New date: {new_date}")
        print(f"   🔑 Service ID: {service_id}")
        print(f"   🔑 Event code: {event_code}")
        
        # Get current timestamp with day of week
        now = datetime.now()
        current_timestamp = f"{now.strftime('%A')}, {now.isoformat()}"
        
        # Get appointment change details from state
        appointment_info = {
            "title_of_event": state.get("change_new_title"),
            "date": state.get("change_new_date"),
            "duration": state.get("change_new_duration"),
            "attendees": state.get("change_new_attendees"),
            "place": state.get("change_new_place"),
            "additional_notes": state.get("change_additional_notes")
        }
        
        # Extract favorite_day from new_date if available (only date part, not time)
        # This avoids LLM miscalculating relative dates like "lunedì prossimo"
        favorite_day = None
        if new_date and isinstance(new_date, str) and 'T' in new_date:
            favorite_day = new_date.split('T')[0]  # Extract YYYY-MM-DD
            print(f"📅 [RESCHEDULER] Pre-extracted favorite_day from reader: {favorite_day}")
        
        # Call LLM rescheduler with tool functions
        rescheduler_response = llm_client.reschedule_appointment(
            current_timestamp=current_timestamp,
            mail_summary=mail_summary,
            extended_summary=extended_summary,
            event_code=event_code,
            propose_slots=propose_slots,
            appointment_info=appointment_info,
            service_id=service_id,
            thread_id=thread_id,
            language=language,
            favorite_day=favorite_day
        )
        
        # Update state with rescheduling results
        state["appointment_scheduled"] = rescheduler_response.scheduled

        if rescheduler_response.scheduled:
            state["status"] = "EVENT_RESCHEDULED"

        state["appointment_overlap"] = rescheduler_response.overlap
        state["appointment_event_code"] = rescheduler_response.event_code
        state["appointment_proposed_slots"] = rescheduler_response.proposed_slots
        state["appointment_favorite_day_unavailable"] = rescheduler_response.favorite_day_unavailable
        state["scheduled_event_details"] = rescheduler_response.event_details
        
        print(f"✅ [RESCHEDULER] Rescheduling completed successfully")
        print(f"   ✓ Scheduled: {rescheduler_response.scheduled}")
        print(f"   ⚠️ Overlap: {rescheduler_response.overlap}")
        print(f"   🔢 Event code: {rescheduler_response.event_code}")
        print(f"   📆 Proposed slots: {rescheduler_response.proposed_slots}")
        print(f"   📅 Favorite day unavailable: {rescheduler_response.favorite_day_unavailable}")
        print(f"   📋 Event details: {'Yes' if rescheduler_response.event_details else 'No'}")
        
        return state
        
    except Exception as e:
        print(f"❌ [RESCHEDULER] Error in appointment rescheduling: {e}")
        # TODO notification and save to db
        return state

        
def cancellation_node(state):
    """
    Cancellations for CANCELLATION subcategory.
    First validates event_code, then uses LLM with tool functions to either delete appointment.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with cancellation results or AutomationExecutedResponse if event_code invalid
    """
    print(f"❌ [CANCELLATION] Processing appointment cancellation")
    
    # Extract necessary information from state
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    category = state.get("category")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")

    # Extract event_code from response
    event_code = state.get("cancellation_event_code")

    if event_code is None or (isinstance(event_code, str) and len(event_code) != 6):
        print(f"⚠️ [CANCELLATION] Invalid event_code: {event_code}")
        state["status"] = "EVENT_CODE_INVALID"
        return state
    
    # Check if event_code is present
    if event_code and isinstance(event_code, str) and len(event_code) == 6:
        print(f"   🔑 Event code found: {event_code}")
        
        try:
            print(f"   🔍 Searching for event {event_code} in database...")

            event_response = get_scheduled_event_by_code(event_code)
            
            if not event_response:
                state["status"] = "EVENT_CODE_NOT_FOUND"
                state["human_response"] = True
                state["automation_executed"] = True
                return state
            
            event_data = event_response
            event_automation_id = event_data.get("event_automation_id")
            service_id = event_data.get("service_id")
            calendar_event_id = event_data.get("provider_event_id")
            
            print(f"   ✅ Event found in database: event_automation_id={event_automation_id}")
            
            # Get calendar service data to determine provider and token
            service_data = get_calendar_service_data(service_id)
            
            if not service_data:
                state["status"] = "CALENDAR_SERVICE_NOT_FOUND"
                state["human_response"] = True
                state["automation_executed"] = True
                return state
            
            calendar_provider = service_data.get("calendar_provider")
            access_token = service_data.get("access_token")
            
            # Delete event from calendar based on provider
            calendar_deleted = False
            if calendar_event_id:
                print(f"   🗑️ Deleting event from {calendar_provider} calendar...")
                if calendar_provider == "google":
                    calendar_deleted = delete_google_calendar_event(access_token, calendar_event_id)
                elif calendar_provider == "microsoft":
                    calendar_deleted = delete_microsoft_calendar_event(access_token, calendar_event_id)
                else:
                    print(f"   ⚠️ Unknown calendar provider: {calendar_provider}")
            
            # Delete event from database
            print(f"   🗑️ Deleting event from scheduled_events table...")
            db_delete_response = delete_event_from_db(event_code)
            
            if db_delete_response and calendar_deleted:
                print(f"   ✅ Event {event_code} successfully deleted")
                state["status"] = "EVENT_DELETED"
                return state
            else:
                state["status"] = "EVENT_DELETION_FAILED"
                state["human_response"] = True
                state["automation_executed"] = True
                return state
                
        except Exception as e:
            #TODO: Send a notification and save in DB
            print(f"   ❌ Error processing cancellation: {e}")
            return state
    else:
        state["status"] = "EVENT_CODE_NOT_FOUND"
        state["human_response"] = True
        state["automation_executed"] = True
        return state

def extractor_company_info_node(state):
    """
    Estrae le informazioni aziendali rilevanti per rispondere all'email.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with chunked_company_informations or AutomationExecutedResponse if info not present
    """
    try:
        print(f"🏢 [EXTRACTOR_COMPANY_INFO] Starting company information extraction")
        
        # Retrieve extracted_info per ottenere box_email
        extracted_info = state.get('extracted_info', {})
        box_email = extracted_info.get('box_email', 'unknown')
        message_id = extracted_info.get('message_id', 'unknown')
        thread_id = extracted_info.get('thread_id', 'unknown')
        from_email = extracted_info.get('from', 'unknown')
        subject = extracted_info.get('subject', 'No Subject')
        
        print(f"   📧 Box email: {box_email}")
        
        # Step 1: Recupera company information dal database
        company_information = get_company_information_sync(box_email)
        print(f"   📝 Company information: {company_information}")
        
        # Step 2: Gestione caso information vuota o non presente
        if not company_information:
            print(f"⚠️ [EXTRACTOR_COMPANY_INFO] Company information not available - sending notification")
            
            state["human_response"] = True
            state["automation_executed"] = True
            state["status"] = "COMPANY_INFO_EXTRACTION_FAILED"
            return state
        
        # Step 3: Estrai informazioni rilevanti tramite LLM
        extended_summary = state.get('extended_summary', '')
        mail_summary = state.get('mail_summary', '')
        summary_attachments = state.get('summary_attachments', '')
        key_entities = state.get('key_entities', {})
        language = state.get('language', 'ITA')

        # Invoca l'LLM per estrarre le informazioni rilevanti
        extraction_result = llm_client.extract_company_info(
            extended_summary=extended_summary,
            mail_summary=mail_summary,
            summary_attachments=summary_attachments,
            key_entities=key_entities,
            company_information=company_information,
            language=language
        )
        
        # Aggiorna lo stato con le informazioni estratte
        state['chunked_company_informations'] = extraction_result.chunked_company_informations

        if extraction_result.chunked_company_informations is None or extraction_result.chunked_company_informations == []:
            state["human_response"] = True
            state["automation_executed"] = True
            state["status"] = "COMPANY_INFO_EXTRACTION_FAILED"
            return state

        # DEBUG
        print(f"✅ [EXTRACTOR_COMPANY_INFO] Company information extracted successfully")

        return state
        
    except Exception as e:
        print(f"❌ [EXTRACTOR_COMPANY_INFO] Error extracting company information: {str(e)}")
        state["human_response"] = True
        state["status"] = "COMPANY_INFO_EXTRACTION_FAILED"
        state["automation_executed"] = True
        return state

def writer_node(state):
    """
    Write email response based on subcategory and context.
    Handles different cases:
    - REQUEST_APPOINTMENT: Uses scheduled, event_code, proposed_slots
    - REQUEST_APPOINTMENT_CHANGE: Uses change_event_code, status, scheduled, event_code, proposed_slots
    - CANCEL_APPOINTMENT: Uses cancellation_event_code, status
    - Other subcategories: Uses generic prompt with company info
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with written_email_body
    """
    try:
        print(f"✍️ [WRITER] Starting email writing...")
        
        # Get common parameters from state
        subcategory = state.get("subcategory", "")
        language = state.get("language", "ITA")
        extended_summary = state.get("extended_summary", "")
        mail_summary = state.get("mail_summary", "")
        chunked_company_info = state.get("chunked_company_informations", {})
        attachment_summary = state.get("summary_attachments", "")
        guidelines = state.get("guidelines", [])
        
        print(f"📋 [WRITER] Writing parameters:")
        print(f"   🏷️ Subcategory: {subcategory}")
        print(f"   🔒 Language: {language}")
        print(f"   📝 Has guidelines: {len(guidelines) if guidelines else 0}")
        
        # Prepare parameters based on subcategory
        if subcategory == "REQUEST_APPOINTMENT":
            # Get appointment-specific parameters
            scheduled = state.get("appointment_scheduled", False)
            event_code = state.get("appointment_event_code")
            proposed_slots = state.get("appointment_proposed_slots")
            favorite_day_unavailable = state.get("appointment_favorite_day_unavailable", False)
            
            print(f"   📅 Scheduled: {scheduled}")
            print(f"   🔢 Event code: {event_code}")
            print(f"   📆 Proposed slots: {proposed_slots}")
            print(f"   ⚠️ Favorite day unavailable: {favorite_day_unavailable}")
            
            # Call LLM to write email
            write_response = llm_client.write_email(
                subcategory=subcategory,
                extended_summary=extended_summary,
                mail_summary=mail_summary,
                chunked_company_info=chunked_company_info,
                attachment_summary=attachment_summary,
                guidelines=guidelines,
                language=language,
                scheduled=scheduled,
                event_code=event_code,
                proposed_slots=proposed_slots,
                favorite_day_unavailable=favorite_day_unavailable
            )
            
        elif subcategory == "REQUEST_APPOINTMENT_CHANGE":
            # Get appointment change-specific parameters
            change_event_code = state.get("change_event_code")
            status = state.get("status", "")
            scheduled = state.get("appointment_scheduled", False)
            event_code = state.get("appointment_event_code")
            proposed_slots = state.get("appointment_proposed_slots")
            favorite_day_unavailable = state.get("appointment_favorite_day_unavailable", False)
            
            print(f"   🔑 Change event code: {change_event_code}")
            print(f"   📊 Status: {status}")
            print(f"   📅 Scheduled: {scheduled}")
            print(f"   🔢 Event code: {event_code}")
            print(f"   📆 Proposed slots: {proposed_slots}")
            print(f"   ⚠️ Favorite day unavailable: {favorite_day_unavailable}")
            
            # Call LLM to write email
            write_response = llm_client.write_email(
                subcategory=subcategory,
                extended_summary=extended_summary,
                mail_summary=mail_summary,
                chunked_company_info=chunked_company_info,
                attachment_summary=attachment_summary,
                guidelines=guidelines,
                language=language,
                change_event_code=change_event_code,
                status=status,
                scheduled=scheduled,
                event_code=event_code,
                proposed_slots=proposed_slots,
                favorite_day_unavailable=favorite_day_unavailable
            )
            
        elif subcategory == "CANCEL_APPOINTMENT":
            # Get cancellation-specific parameters
            cancellation_event_code = state.get("cancellation_event_code")
            status = state.get("status", "")
            
            print(f"   🔑 Cancellation event code: {cancellation_event_code}")
            print(f"   📊 Status: {status}")
            
            # Call LLM to write email
            write_response = llm_client.write_email(
                subcategory=subcategory,
                extended_summary=extended_summary,
                mail_summary=mail_summary,
                chunked_company_info=chunked_company_info,
                attachment_summary=attachment_summary,
                guidelines=guidelines,
                language=language,
                cancellation_event_code=cancellation_event_code,
                status=status
            )
        
        elif subcategory == "CONFIRM_APPOINTMENT":
            # Get confirm appointment-specific parameters
            scheduled = state.get("appointment_scheduled")
            event_code = state.get("appointment_event_code")
            proposed_slots = state.get("appointment_proposed_slots")
            favorite_day_unavailable = state.get("appointment_favorite_day_unavailable", False)
            
            print(f"   📅 Scheduled: {scheduled}")
            print(f"   🔢 Event code: {event_code}")
            print(f"   📆 Proposed slots: {proposed_slots}")
            print(f"   ⚠️ Favorite day unavailable: {favorite_day_unavailable}")
            
            # If already_scheduled=False, it went through scheduler and needs appointment-specific response
            # If already_scheduled=True, use generic prompt (scheduled will be None)
            write_response = llm_client.write_email(
                subcategory=subcategory,
                extended_summary=extended_summary,
                mail_summary=mail_summary,
                chunked_company_info=chunked_company_info,
                attachment_summary=attachment_summary,
                guidelines=guidelines,
                language=language,
                scheduled=scheduled,
                event_code=event_code,
                proposed_slots=proposed_slots,
                favorite_day_unavailable=favorite_day_unavailable
            )
            
        else:
            # Generic case for all other subcategories
            print(f"   📝 Using generic writer prompt")
            
            # Call LLM to write email
            write_response = llm_client.write_email(
                subcategory=subcategory,
                extended_summary=extended_summary,
                mail_summary=mail_summary,
                chunked_company_info=chunked_company_info,
                attachment_summary=attachment_summary,
                guidelines=guidelines,
                language=language
            )
        
        # Update state with written email
        state["written_email_body"] = write_response.written_email_body
        
        # Update edit history with modifications summary from LLM
        # Only append if there's a meaningful summary (guidelines were applied)
        if write_response.modifications_summary and write_response.modifications_summary.strip():
            edit_history = state.get("edit_history", [])
            edit_history.append(write_response.modifications_summary)
            state["edit_history"] = edit_history
            
            print(f"✅ [WRITER] Email written successfully")
            print(f"   📝 Email length: {len(write_response.written_email_body)} characters")
            print(f"   🗓️ Edit history entries: {len(edit_history)}")
            print(f"   ✏️  Modifications: {write_response.modifications_summary}")
        else:
            print(f"✅ [WRITER] Email written successfully (no modifications to track)")
            print(f"   📝 Email length: {len(write_response.written_email_body)} characters")
        
        return state
        
    except Exception as e:
        print(f"❌ [WRITER] Error writing email: {e}")
        # Set error message in state
        state["written_email_body"] = "Error generating email response."
        state["status"] = "WRITER_ERROR"
        return state

def reviewer_node(state):
    """
    Review the written email and provide feedback.
    Uses LLM to assess email quality against context and company information.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with review results (needs_review, correctness_score, guidelines)
    """
    try:
        print(f"📝 [REVIEWER] Starting email review...")
        
        # Get current iteration and increment
        current_iteration = state.get("review_iteration", 0)
        state["review_iteration"] = current_iteration + 1
        
        # Get required parameters from state
        written_email_body = state.get("written_email_body", "")
        chunked_company_info = state.get("chunked_company_informations", {})
        extended_summary = state.get("extended_summary", "")
        mail_summary = state.get("mail_summary", "")
        edit_history = state.get("edit_history", [])
        language = state.get("language", "ITA")
        
        # Build appointment context if applicable
        appointment_context = None
        subcategory = state.get("subcategory")
        
        # Check if this is an appointment-related subcategory
        appointment_subcategories = [
            "REQUEST_APPOINTMENT", "REQUEST_APPOINTMENT_CHANGE", "CANCEL_APPOINTMENT", "CONFIRM_APPOINTMENT"
        ]
        
        # Get subcategory value (handle enum or string)
        subcategory_value = subcategory.value if hasattr(subcategory, 'value') else subcategory
        
        if subcategory_value in appointment_subcategories:
            appointment_context = {
                "scheduled": state.get("appointment_scheduled"),
                "rescheduled": state.get("appointment_scheduled") and subcategory_value in ["REQUEST_APPOINTMENT_CHANGE", "CONFIRM_APPOINTMENT"] and state.get("change_event_code"),
                "event_code": state.get("appointment_event_code"),
                "proposed_slots": state.get("appointment_proposed_slots"),
                "overlap": state.get("appointment_overlap"),
                "change_event_code": state.get("change_event_code"),
                "cancellation_event_code": state.get("cancellation_event_code"),
                "cancelled": state.get("cancellation_event_code") and subcategory_value == "CANCEL_APPOINTMENT" and state.get("automation_executed"),
                "operation_status": state.get("status"),  # Include operation status (EVENT_CODE_INVALID, EVENT_DELETED, EVENT_RESCHEDULED, etc.)
            }
            print(f"   📅 Appointment context built for subcategory: {subcategory_value}")
        
        print(f"   🔢 Review iteration: {state['review_iteration']}")
        
        # Call LLM to review the email
        review_response = llm_client.review_email(
            written_email_body=written_email_body,
            chunked_company_info=chunked_company_info,
            extended_summary=extended_summary,
            mail_summary=mail_summary,
            edit_history=edit_history,
            language=language,
            appointment_context=appointment_context
        )
        
        # Update state with review results
        state["needs_review"] = review_response.needs_review
        state["correctness_score"] = review_response.correctness_score
        state["guidelines"] = review_response.guidelines if review_response.guidelines else []
        
        # Check if we should loop back to writer
        should_loop = (
            state["needs_review"] and 
            state["correctness_score"] < CORRECTNESS_THRESHOLD and 
            state["review_iteration"] < MAX_REVIEW_ITERATIONS
        )
        
        if should_loop:
            print(f"🔁 [REVIEWER] Looping back to WRITER (iteration {state['review_iteration'] + 1})")
            # State remains as is, graph will route back to WRITER based on needs_review/correctness
        else:
            # End of loop - determine final status
            if state["needs_review"] and state["correctness_score"] < CORRECTNESS_THRESHOLD:
                print(f"⚠️ [REVIEWER] Low confidence writing - needs review")
                state["status"] = "LOW_CONFIDENCE_WRITER"
                state["human_response"] = True
                state["automation_executed"] = True
            else:
                print(f"✅ [REVIEWER] Email ready to send")
                state["status"] = "EMAIL_READY_TO_SEND"
                state["automation_executed"] = True
        
        return state
        
    except Exception as e:
        print(f"❌ [REVIEWER] Error in review: {e}")
        # TODO: On error, don't require review and pass through
        state["needs_review"] = False
        state["correctness_score"] = 0.8
        state["guidelines"] = []
        return state
        
    except Exception as e:
        print(f"❌ [SENDER] Error preparing email: {e}")
        state["status"] = "SENDER_ERROR"
        state["human_response"] = True
        state["automation_executed"] = True
        return state