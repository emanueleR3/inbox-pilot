"""
Core workflow nodes for email processing.
"""

import os
from langgraph.graph import END
from .config import NodeNames
from ..llm.client import llm_client
from ..models.llm_responses import DangerousEmailDetected, LowConfidenceClassification, AutomationExecutedResponse
from db_client import get_supabase_client, get_calendar_service_data, get_scheduled_event_by_code
from ec_system.utils.utils import delete_google_calendar_event, delete_microsoft_calendar_event
from datetime import datetime

# Import db_client for user configuration and notifications
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
from db_client import get_user_configuration_sync, get_default_configuration, insert_notification_sync, get_email_attachments_sync, get_company_information_sync

# Import attachment extractor service
from ..services.attachment_extractor import attachment_extractor
# Import notification client
from ..services.notification_client import send_low_confidence_notification, send_high_priority_notification, send_event_invite_notification, send_information_not_present_notification
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
            # Low confidence - terminate workflow
            print(f"⚠️ [CLASSIFIER] Low confidence classification detected")
            print(f"   🏷️ Category: {classification_response.category}")
            print(f"   📊 Confidence: {classification_response.confidence_score}")
            print(f"   🎯 Threshold: {confidence_threshold} (FAILED)")
            print(f"   � Workflow terminated - human review required")
            
            # Get extracted info for notifications
            extracted_info = state.get("extracted_info", {})
            message_id = extracted_info.get("message_id", "unknown")
            box_email = extracted_info.get("box_email", "unknown")
            
            # Insert notification in database
            try:
                notification_success = insert_notification_sync(
                    email=box_email,
                    notification_type="LOW_CONFIDENCE_CLASSIFICATION_MAIL",
                    message_id=message_id,
                    text=None
                )
                
                if not notification_success:
                    print(f"❌ [CLASSIFIER] Failed to insert notification for {box_email}")
                    
            except Exception as e:
                print(f"❌ [CLASSIFIER] Error inserting notification: {e}")
            
            # Send notification webhook for low confidence classification
            send_low_confidence_notification(
                sender_email=extracted_info.get("from", "unknown"),
                box_email=box_email,
                subject=extracted_info.get("subject", "No subject"),
                body=state.get("email_body", ""),
                summary_attachment=state.get("summary_attachments")
            )
            
            # Return low confidence classification for workflow termination
            return LowConfidenceClassification(
                message_id=message_id,
                thread_id=thread_id,
                message=f"Classification confidence {classification_response.confidence_score} below threshold {confidence_threshold}",
                result={
                    "category": classification_response.category,
                    "confidence_score": classification_response.confidence_score,
                    "mail_summary": state.get("mail_summary", ""),
                    "extended_summary": state.get("extended_summary", "")
                }
            )
        
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
    
    # DEBUG: Print all state keys to see what's available
    print(f"   🔍 [DEBUG] State keys: {list(state.keys())}")
    
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
        
        # CONSOLE OUTPUT: Print the summary for debugging
        print(f"")
        print(f"📋 [ATTACHMENT_SUMMARY] GENERATED SUMMARY:")
        print(f"=" * 80)
        print(summary_response.summary_attachments)
        print(f"=" * 80)
        print()
        
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
            print(f"⚠️ [EVALUATOR] Evaluation response is None, using default evaluation")

            # save in db
            from db_client import insert_notification_sync
            # Get extracted info for notifications
            extracted_info = state.get("extracted_info", {})
            message_id = extracted_info.get("message_id", "unknown")
            box_email = extracted_info.get("box_email", "unknown")
            # Insert notification in database
            try:
                notification_success = insert_notification_sync(
                    email=box_email,
                    notification_type="LOW_CONFIDENCE_CLASSIFICATION_MAIL",
                    message_id=message_id,
                    text=None
                )
                
                if not notification_success:
                    print(f"❌ [EVALUATOR] Failed to insert notification for {box_email}")
            except Exception as e:
                print(f"❌ [EVALUATOR] Error inserting notification: {e}")

            send_low_confidence_notification(
                sender_email=extracted_info.get("from", "unknown"),
                box_email=extracted_info.get("box_email", "unknown"),
                subject=extracted_info.get("subject", "No subject"),
                body=state.get("email_body", ""),
                summary_attachment=state.get("summary_attachments")
            )
        
        # Update state with evaluation results
        state["priority_score"] = evaluation_response.priority_score
        state["subcategory"] = evaluation_response.subcategory
        
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
        print(f"   📏 Threshold: {priority_threshold}")
        print(f"   🏷️ Subcategory: {subcategory}")
        
        # Determine routing based on priority
        if priority_score >= priority_threshold:
            print(f"🚨 [PRIORITY_CONTROLLER] HIGH PRIORITY EMAIL")
            print(f"   ⚡ Score {priority_score} >= Threshold {priority_threshold}")
            
            """
            # Get extracted info for notifications
            extracted_info = state.get("extracted_info", {})
            message_id = extracted_info.get("message_id", "unknown")
            box_email = extracted_info.get("box_email", "unknown")
            # Insert notification in database
            try:
                notification_success = insert_notification_sync(
                    email=box_email,
                    notification_type="HIGH_PRIORITY_MAIL",
                    message_id=message_id,
                    text=None
                )
                
                if not notification_success:
                    print(f"❌ [PRIORITY_CONTROLLER] Failed to insert notification for {box_email}")
                    
            except Exception as e:
                print(f"❌ [PRIORITY_CONTROLLER] Error inserting notification: {e}")
            
            # Send notification webhook for high priority email
            send_high_priority_notification(
                sender_email=extracted_info.get("from", "unknown"),
                box_email=box_email,
                subject=extracted_info.get("subject", "No subject"),
                body=state.get("email_body", ""),
                summary_attachment=state.get("summary_attachments")
            )
            """

            # Mark for high priority handling
            state["high_priority_email"] = True
            state["workflow_decision"] = "END_HIGH_PRIORITY"
            return state
        else:
            print(f"📋 [PRIORITY_CONTROLLER] Normal priority - Routing to subcategory handler")
            print(f"   📊 Score {priority_score} < Threshold {priority_threshold}")
            # Continue to subcategory routing
            state["high_priority_email"] = False
            state["workflow_decision"] = "ROUTE_TO_SUBCATEGORY"
            return state
            
    except Exception as e:
        # TODO Send notification and save to database
        print(f"❌ [PRIORITY_CONTROLLER] Error in priority control: {e}")
        # Default to normal priority on error
        state["high_priority_email"] = False
        state["workflow_decision"] = "ROUTE_TO_SUBCATEGORY"
        return state


# SUBCATEGORY HANDLER NODES
def handle_offer_promotion_node(state):
    """Handle OFFER_PROMOTION subcategory emails - automated processing."""
    print(f"🎯 [OFFER_PROMOTION] Processing promotional offer email (automated)")
    
    # Extract necessary information from state
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    category = state.get("category")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")
    summary_attachments = state.get("summary_attachments", "")
    
    # Create extended summary combining mail summary and attachments
    extended_parts = []
    if mail_summary:
        extended_parts.append(f"Contenuto email: {mail_summary}")
    if summary_attachments:
        extended_parts.append(f"Allegati: {summary_attachments}")
    
    extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🤖 Automation: Archiviata automaticamente come promozione")
    
    
    
    
    # Return automation executed response
    return AutomationExecutedResponse(
        message_id=message_id,
        thread_id=thread_id,
        status="automation_executed",
        message="Email promozionale archiviata automaticamente",
        result={
            "category": category,
            "subcategory": subcategory,
            "human_response": False,
            "mail_summary": mail_summary,
            "extended_summary": extended_summary
        }
    )


def handle_newsletter_node(state):
    """Handle NEWSLETTER subcategory emails - automated processing."""
    print(f"📰 [NEWSLETTER] Processing newsletter email (automated)")
    
    # Extract necessary information from state
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    category = state.get("category")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")
    summary_attachments = state.get("summary_attachments", "")
    
    # Create extended summary combining mail summary and attachments
    extended_parts = []
    if mail_summary:
        extended_parts.append(f"Contenuto email: {mail_summary}")
    if summary_attachments:
        extended_parts.append(f"Allegati: {summary_attachments}")
    
    extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🤖 Automation: Archiviata automaticamente come newsletter")
    
    
    
    
    # Return automation executed response
    return AutomationExecutedResponse(
        message_id=message_id,
        thread_id=thread_id,
        status="automation_executed",
        message="Newsletter archiviata automaticamente",
        result={
            "category": category,
            "subcategory": subcategory,
            "human_response": False,
            "mail_summary": mail_summary,
            "extended_summary": extended_summary
        }
    )


def handle_event_invite_node(state):
    """Handle EVENT_INVITE subcategory emails - conditional processing."""
    print(f"🎉 [EVENT_INVITE] Processing event invitation email")
    
    category = state.get("category")
    extracted_info = state.get("extracted_info", {})
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🏷️ Category: {category}")
    
    # If category is promotion or social_notification, automate
    if category in ["PROMOTION", "SOCIAL_NOTIFICATION"]:
        print(f"   🤖 Automation: Category {category} - Archiviata automaticamente")
        
        message_id = extracted_info.get("message_id")
        thread_id = extracted_info.get("thread_id")
        subcategory = state.get("subcategory")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        # Create extended summary
        extended_parts = []
        if mail_summary:
            extended_parts.append(f"Contenuto email: {mail_summary}")
        if summary_attachments:
            extended_parts.append(f"Allegati: {summary_attachments}")
        
        extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
        
        
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message=f"Invito evento (categoria {category}) archiviato automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": False,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )
    else:
        # Get message details for notification
        message_id = extracted_info.get("message_id")
        thread_id = extracted_info.get("thread_id")
        box_email = extracted_info.get("box_email", "unknown")
        subcategory = state.get("subcategory")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        # Create extended summary
        extended_parts = []
        if mail_summary:
            extended_parts.append(f"Contenuto email: {mail_summary}")
        if summary_attachments:
            extended_parts.append(f"Allegati: {summary_attachments}")
        
        extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
        
        # Insert notification in database
        try:
            notification_success = insert_notification_sync(
                email=box_email,
                notification_type="EVENT_INVITE_MAIL",
                message_id=message_id,
                text=None
            )
            
            if not notification_success:
                print(f"❌ [EVENT_INVITE] Failed to insert notification for {box_email}")
                
        except Exception as e:
            print(f"❌ [EVENT_INVITE] Error inserting notification: {e}")
        
        # Send notification webhook for event invite requiring human response
        send_event_invite_notification(
            sender_email=extracted_info.get("from", "unknown"),
            box_email=box_email,
            subject=extracted_info.get("subject", "No subject"),
            body=state.get("email_body", ""),
            summary_attachment=state.get("summary_attachments")
        )

        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message=f"Invito evento (categoria {category}) archiviato automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": True,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )


def handle_product_update_node(state):
    """Handle PRODUCT_UPDATE subcategory emails - conditional processing."""
    print(f"📦 [PRODUCT_UPDATE] Processing product update email")
    
    category = state.get("category")
    extracted_info = state.get("extracted_info", {})
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🏷️ Category: {category}")
    
    # If category is promotion, automate
    if category == "PROMOTION":
        print(f"   🤖 Automation: Category PROMOTION - Archiviata automaticamente")
        
        message_id = extracted_info.get("message_id")
        thread_id = extracted_info.get("thread_id")
        subcategory = state.get("subcategory")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        # Create extended summary
        extended_parts = []
        if mail_summary:
            extended_parts.append(f"Contenuto email: {mail_summary}")
        if summary_attachments:
            extended_parts.append(f"Allegati: {summary_attachments}")
        
        extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
        
        
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Aggiornamento prodotto promozionale archiviato automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": False,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )
    else:
        return state


def handle_request_quote_node(state):
    """Handle REQUEST_QUOTE subcategory emails."""
    print(f"💰 [REQUEST_QUOTE] Processing quote request email")
    
    category = state.get("category")
    extracted_info = state.get("extracted_info", {})
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🏷️ Category: {category}")
    
    # If category is transactional, automate
    if category == "PROMOTION":
        print(f"   🤖 Automation: Category PROMOTION - Archiviata automaticamente")
        
        message_id = extracted_info.get("message_id")
        thread_id = extracted_info.get("thread_id")
        subcategory = state.get("subcategory")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        # Create extended summary
        extended_parts = []
        if mail_summary:
            extended_parts.append(f"Contenuto email: {mail_summary}")
        if summary_attachments:
            extended_parts.append(f"Allegati: {summary_attachments}")
        
        extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Documenti inviati (transazionale) archiviato automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": False,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )
    else:
        # TODO ci sarebbe da controllare la configurazione "response_to_quote"
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Documenti inviati (transazionale) archiviato automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": True,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )


def handle_new_message_node(state):
    """Handle NEW_MESSAGE subcategory emails - automated processing."""
    print(f"💬 [NEW_MESSAGE] Processing new message notification (automated)")
    
    # Extract necessary information from state
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    category = state.get("category")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")
    summary_attachments = state.get("summary_attachments", "")
    
    # Create extended summary combining mail summary and attachments
    extended_parts = []
    if mail_summary:
        extended_parts.append(f"Contenuto email: {mail_summary}")
    if summary_attachments:
        extended_parts.append(f"Allegati: {summary_attachments}")
    
    extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🤖 Automation: Archiviata automaticamente come notifica messaggio")
    
    
    
    
    # Return automation executed response
    return AutomationExecutedResponse(
        message_id=message_id,
        thread_id=thread_id,
        status="automation_executed",
        message="Notifica nuovo messaggio archiviata automaticamente",
        result={
            "category": category,
            "subcategory": subcategory,
            "human_response": False,
            "mail_summary": mail_summary,
            "extended_summary": extended_summary
        }
    )


def handle_connection_request_node(state):
    """Handle CONNECTION_REQUEST subcategory emails - conditional processing."""
    print(f"🤝 [CONNECTION_REQUEST] Processing connection request")
    
    category = state.get("category")
    extracted_info = state.get("extracted_info", {})
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🏷️ Category: {category}")
    
    # If category is social_notification, automate
    if category == "SOCIAL_NOTIFICATION":
        print(f"   🤖 Automation: Category SOCIAL_NOTIFICATION - Archiviata automaticamente")
        
        message_id = extracted_info.get("message_id")
        thread_id = extracted_info.get("thread_id")
        subcategory = state.get("subcategory")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        # Create extended summary
        extended_parts = []
        if mail_summary:
            extended_parts.append(f"Contenuto email: {mail_summary}")
        if summary_attachments:
            extended_parts.append(f"Allegati: {summary_attachments}")
        
        extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
        
        
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Richiesta connessione social archiviata automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": False,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )
    else:
        return state


def handle_system_alert_node(state):
    """Handle SYSTEM_ALERT subcategory emails - automated processing."""
    print(f"⚠️ [SYSTEM_ALERT] Processing system alert (automated)")
    
    # Extract necessary information from state
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    category = state.get("category")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")
    summary_attachments = state.get("summary_attachments", "")
    
    # Create extended summary combining mail summary and attachments
    extended_parts = []
    if mail_summary:
        extended_parts.append(f"Contenuto email: {mail_summary}")
    if summary_attachments:
        extended_parts.append(f"Allegati: {summary_attachments}")
    
    extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🤖 Automation: Archiviata automaticamente come alert di sistema")
    
    
    
    
    # Return automation executed response
    return AutomationExecutedResponse(
        message_id=message_id,
        thread_id=thread_id,
        status="automation_executed",
        message="Alert di sistema archiviato automaticamente",
        result={
            "category": category,
            "subcategory": subcategory,
            "human_response": False,
            "mail_summary": mail_summary,
            "extended_summary": extended_summary
        }
    )


def handle_system_notification_node(state):
    """Handle SYSTEM_NOTIFICATION subcategory emails - automated processing."""
    print(f"🔔 [SYSTEM_NOTIFICATION] Processing system notification (automated)")
    
    # Extract necessary information from state
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    category = state.get("category")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")
    summary_attachments = state.get("summary_attachments", "")
    
    # Create extended summary combining mail summary and attachments
    extended_parts = []
    if mail_summary:
        extended_parts.append(f"Contenuto email: {mail_summary}")
    if summary_attachments:
        extended_parts.append(f"Allegati: {summary_attachments}")
    
    extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🤖 Automation: Archiviata automaticamente come notifica di sistema")
    
    
    
    
    # Return automation executed response
    return AutomationExecutedResponse(
        message_id=message_id,
        thread_id=thread_id,
        status="automation_executed",
        message="Notifica di sistema archiviata automaticamente",
        result={
            "category": category,
            "subcategory": subcategory,
            "human_response": False,
            "mail_summary": mail_summary,
            "extended_summary": extended_summary
        }
    )


def handle_sent_documents_node(state):
    """Handle SENT_DOCUMENTS subcategory emails - conditional processing."""
    print(f"📄 [SENT_DOCUMENTS] Processing document delivery notification")
    
    category = state.get("category")
    extracted_info = state.get("extracted_info", {})
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🏷️ Category: {category}")
    
    # If category is transactional, automate
    if category == "TRANSACTIONAL":
        print(f"   🤖 Automation: Category TRANSACTIONAL - Archiviata automaticamente")
        
        message_id = extracted_info.get("message_id")
        thread_id = extracted_info.get("thread_id")
        subcategory = state.get("subcategory")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        # Create extended summary
        extended_parts = []
        if mail_summary:
            extended_parts.append(f"Contenuto email: {mail_summary}")
        if summary_attachments:
            extended_parts.append(f"Allegati: {summary_attachments}")
        
        extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
        
        
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Documenti inviati (transazionale) archiviato automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": False,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )
    else:
        return state


def handle_provide_update_node(state):
    """Handle PROVIDE_UPDATE subcategory emails - conditional processing."""
    print(f"📈 [PROVIDE_UPDATE] Processing status update")
    
    category = state.get("category")
    extracted_info = state.get("extracted_info", {})
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🏷️ Category: {category}")
    
    # If category is transactional, automate
    if category == "TRANSACTIONAL":
        print(f"   🤖 Automation: Category TRANSACTIONAL - Archiviata automaticamente")
        
        message_id = extracted_info.get("message_id")
        thread_id = extracted_info.get("thread_id")
        subcategory = state.get("subcategory")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        # Create extended summary
        extended_parts = []
        if mail_summary:
            extended_parts.append(f"Contenuto email: {mail_summary}")
        if summary_attachments:
            extended_parts.append(f"Allegati: {summary_attachments}")
        
        extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
        
        
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Aggiornamento stato (transazionale) archiviato automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": False,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )
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

    # Extract necessary information from state
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    category = state.get("category")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")
    summary_attachments = state.get("summary_attachments", "")
    
    # Create extended summary combining mail summary and attachments
    extended_parts = []
    if mail_summary:
        extended_parts.append(f"Contenuto email: {mail_summary}")
    if summary_attachments:
        extended_parts.append(f"Allegati: {summary_attachments}")
    
    extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🤖 Automation: Archiviata automaticamente come alert di sistema")
    
    # Return automation executed response
    return AutomationExecutedResponse(
        message_id=message_id,
        thread_id=thread_id,
        status="automation_executed",
        message="Alert di sistema archiviato automaticamente",
        result={
            "category": category,
            "subcategory": subcategory,
            "human_response": True,
            "mail_summary": mail_summary,
            "extended_summary": extended_summary
        }
    )


def handle_event_followup_node(state):
    """Handle EVENT_FOLLOWUP subcategory emails."""
    print(f"🔄 [EVENT_FOLLOWUP] Processing event follow-up")
    extracted_info = state.get("extracted_info", {})
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    # TODO: Implement specific logic for event follow-ups
    return state


def handle_invoice_or_receipt_node(state):
    """Handle INVOICE_OR_RECEIPT subcategory emails - conditional processing."""
    print(f"🧾 [INVOICE_OR_RECEIPT] Processing invoice or receipt")
    
    category = state.get("category")
    extracted_info = state.get("extracted_info", {})
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🏷️ Category: {category}")
    
    # If category is transactional, automate
    if category == "TRANSACTIONAL":
        print(f"   🤖 Automation: Category TRANSACTIONAL - Archiviata automaticamente")
        
        message_id = extracted_info.get("message_id")
        thread_id = extracted_info.get("thread_id")
        subcategory = state.get("subcategory")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        # Create extended summary
        extended_parts = []
        if mail_summary:
            extended_parts.append(f"Contenuto email: {mail_summary}")
        if summary_attachments:
            extended_parts.append(f"Allegati: {summary_attachments}")
        
        extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
        
        
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Fattura/ricevuta (transazionale) archiviata automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": False,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )
    else:
        return state


def handle_status_notification_node(state):
    """Handle STATUS_NOTIFICATION subcategory emails - conditional processing."""
    print(f"📊 [STATUS_NOTIFICATION] Processing status notification")
    
    category = state.get("category")
    extracted_info = state.get("extracted_info", {})
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🏷️ Category: {category}")
    
    # If category is transactional, automate
    if category == "TRANSACTIONAL":
        print(f"   🤖 Automation: Category TRANSACTIONAL - Archiviata automaticamente")
        
        message_id = extracted_info.get("message_id")
        thread_id = extracted_info.get("thread_id")
        subcategory = state.get("subcategory")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        # Create extended summary
        extended_parts = []
        if mail_summary:
            extended_parts.append(f"Contenuto email: {mail_summary}")
        if summary_attachments:
            extended_parts.append(f"Allegati: {summary_attachments}")
        
        extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
        
        
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Notifica stato (transazionale) archiviata automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": False,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )
    else:
        return state


def handle_ticket_update_node(state):
    """Handle TICKET_UPDATE subcategory emails - conditional processing."""
    print(f"🎫 [TICKET_UPDATE] Processing ticket update")
    
    category = state.get("category")
    extracted_info = state.get("extracted_info", {})
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🏷️ Category: {category}")
    
    # If category is transactional, automate
    if category == "TRANSACTIONAL":
        print(f"   🤖 Automation: Category TRANSACTIONAL - Archiviata automaticamente")
        
        message_id = extracted_info.get("message_id")
        thread_id = extracted_info.get("thread_id")
        subcategory = state.get("subcategory")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        # Create extended summary
        extended_parts = []
        if mail_summary:
            extended_parts.append(f"Contenuto email: {mail_summary}")
        if summary_attachments:
            extended_parts.append(f"Allegati: {summary_attachments}")
        
        extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
        
        
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Aggiornamento ticket (transazionale) archiviato automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": False,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )
    else:
        return state


def handle_general_greeting_node(state):
    """Handle GENERAL_GREETING subcategory emails."""
    print(f"👋 [GENERAL_GREETING] Processing general greeting")
    extracted_info = state.get("extracted_info", {})
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    # TODO: Implement specific logic for general greetings
    return state


def handle_request_appointment_node(state):
    """Handle REQUEST_APPOINTMENT subcategory emails."""
    print(f"📅 [REQUEST_APPOINTMENT] Processing appointment request")
    extracted_info = state.get("extracted_info", {})
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    # TODO: Implement specific logic for appointment requests
    return state


def handle_request_appointment_change_node(state):
    """Handle REQUEST_APPOINTMENT_CHANGE subcategory emails."""
    print(f"🔄 [REQUEST_APPOINTMENT_CHANGE] Processing appointment change request")
    extracted_info = state.get("extracted_info", {})
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    # TODO: Implement specific logic for appointment changes
    return state


def handle_request_status_update_node(state):
    """Handle REQUEST_STATUS_UPDATE subcategory emails - conditional processing."""
    print(f"📊 [REQUEST_STATUS_UPDATE] Processing status update request")
    
    category = state.get("category")
    extracted_info = state.get("extracted_info", {})
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🏷️ Category: {category}")
    
    # If category is transactional, automate
    if category == "TRANSACTIONAL":
        print(f"   🤖 Automation: Category TRANSACTIONAL - Archiviata automaticamente")
        
        message_id = extracted_info.get("message_id")
        thread_id = extracted_info.get("thread_id")
        subcategory = state.get("subcategory")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        # Create extended summary
        extended_parts = []
        if mail_summary:
            extended_parts.append(f"Contenuto email: {mail_summary}")
        if summary_attachments:
            extended_parts.append(f"Allegati: {summary_attachments}")
        
        extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
        
        
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Richiesta aggiornamento stato (transazionale) archiviata automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": False,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )
    else:
        return state


def handle_ask_for_help_node(state):
    """Handle ASK_FOR_HELP subcategory emails - conditional processing."""
    print(f"🆘 [ASK_FOR_HELP] Processing help request")
    
    category = state.get("category")
    extracted_info = state.get("extracted_info", {})
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🏷️ Category: {category}")
    
    # If category is transactional, automate
    if category == "TRANSACTIONAL":
        print(f"   🤖 Automation: Category TRANSACTIONAL - Archiviata automaticamente")
        
        message_id = extracted_info.get("message_id")
        thread_id = extracted_info.get("thread_id")
        subcategory = state.get("subcategory")
        mail_summary = state.get("mail_summary", "")
        summary_attachments = state.get("summary_attachments", "")
        
        # Create extended summary
        extended_parts = []
        if mail_summary:
            extended_parts.append(f"Contenuto email: {mail_summary}")
        if summary_attachments:
            extended_parts.append(f"Allegati: {summary_attachments}")
        
        extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
        
        
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Richiesta aiuto (transazionale) archiviata automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": False,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )
    else:
        return state


def handle_general_inquiry_node(state):
    """Handle GENERAL_INQUIRY subcategory emails."""
    print(f"❓ [GENERAL_INQUIRY] Processing general inquiry")
    extracted_info = state.get("extracted_info", {})
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    # TODO: Implement specific logic for general inquiries
    return state


def handle_payment_issue_node(state):
    """Handle PAYMENT_ISSUE subcategory emails - conditional processing."""
    print(f"💳 [PAYMENT_ISSUE] Processing payment issue")
    
    category = state.get("category")
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")
    summary_attachments = state.get("summary_attachments", "")
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🏷️ Category: {category}")
    
    # Create extended summary
    extended_parts = []
    if mail_summary:
        extended_parts.append(f"Contenuto email: {mail_summary}")
    if summary_attachments:
        extended_parts.append(f"Allegati: {summary_attachments}")
    
    extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
    
    # If category is transactional, automate without human response
    if category == "TRANSACTIONAL":
        print(f"   🤖 Automation: Category TRANSACTIONAL - Archiviata automaticamente (no human response)")
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Problema pagamento (transazionale) archiviato automaticamente",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": False,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )
    else:
        # Other categories require human response
        print(f"   👤 Human Response Required: Category {category} - Requires human attention")
        
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message=f"Problema pagamento (categoria {category}) richiede attenzione umana",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": True,
                "mail_summary": mail_summary,
                "extended_summary": extended_summary
            }
        )

def handle_cancel_appointment_node(state):
    """Handle CANCEL_APPOINTMENT subcategory emails."""
    print(f"❌ [CANCEL_APPOINTMENT] Processing appointment cancellation")
    extracted_info = state.get("extracted_info", {})
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    # TODO: Implement specific logic for appointment requests
    return state
    
def handle_order_confirmation_node(state):
    """Handle ORDER_CONFIRMATION subcategory emails - automated processing."""
    print(f"🛒 [ORDER_CONFIRMATION] Processing order confirmation (automated)")
    
    # Extract necessary information from state
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    category = state.get("category")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")
    summary_attachments = state.get("summary_attachments", "")
    
    # Create extended summary combining mail summary and attachments
    extended_parts = []
    if mail_summary:
        extended_parts.append(f"Contenuto email: {mail_summary}")
    if summary_attachments:
        extended_parts.append(f"Allegati: {summary_attachments}")
    
    extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🤖 Automation: Archiviata automaticamente come conferma ordine")
    
    # Return automation executed response
    return AutomationExecutedResponse(
        message_id=message_id,
        thread_id=thread_id,
        status="automation_executed",
        message="Conferma ordine archiviata automaticamente",
        result={
            "category": category,
            "subcategory": subcategory,
            "human_response": False,
            "mail_summary": mail_summary,
            "extended_summary": extended_summary
        }
    )


def handle_account_verification_node(state):
    """Handle ACCOUNT_VERIFICATION subcategory emails - automated processing."""
    print(f"🔐 [ACCOUNT_VERIFICATION] Processing account verification (automated)")
    
    # Extract necessary information from state
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    category = state.get("category")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")
    summary_attachments = state.get("summary_attachments", "")
    
    # Create extended summary combining mail summary and attachments
    extended_parts = []
    if mail_summary:
        extended_parts.append(f"Contenuto email: {mail_summary}")
    if summary_attachments:
        extended_parts.append(f"Allegati: {summary_attachments}")
    
    extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🤖 Automation: Archiviata automaticamente come verifica account")
    
    
    
    
    # Return automation executed response
    return AutomationExecutedResponse(
        message_id=message_id,
        thread_id=thread_id,
        status="automation_executed",
        message="Verifica account archiviata automaticamente",
        result={
            "category": category,
            "subcategory": subcategory,
            "human_response": False,
            "mail_summary": mail_summary,
            "extended_summary": extended_summary
        }
    )


def handle_internal_note_node(state):
    """Handle INTERNAL_NOTE subcategory emails - automated processing."""
    print(f"📝 [INTERNAL_NOTE] Processing internal note (automated)")
    
    # Extract necessary information from state
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    category = state.get("category")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")
    summary_attachments = state.get("summary_attachments", "")
    
    # Create extended summary combining mail summary and attachments
    extended_parts = []
    if mail_summary:
        extended_parts.append(f"Contenuto email: {mail_summary}")
    if summary_attachments:
        extended_parts.append(f"Allegati: {summary_attachments}")
    
    extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🤖 Automation: Archiviata automaticamente come nota interna")
    
    
    
    
    # Return automation executed response
    return AutomationExecutedResponse(
        message_id=message_id,
        thread_id=thread_id,
        status="automation_executed",
        message="Nota interna archiviata automaticamente",
        result={
            "category": category,
            "subcategory": subcategory,
            "human_response": False,
            "mail_summary": mail_summary,
            "extended_summary": extended_summary
        }
    )


def handle_spam_or_unknown_node(state):
    """Handle SPAM_OR_UNKNOWN subcategory emails - automated processing."""
    print(f"🚫 [SPAM_OR_UNKNOWN] Processing spam or unknown content (automated)")
    
    # Extract necessary information from state
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    category = state.get("category")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")
    summary_attachments = state.get("summary_attachments", "")
    
    # Create extended summary combining mail summary and attachments
    extended_parts = []
    if mail_summary:
        extended_parts.append(f"Contenuto email: {mail_summary}")
    if summary_attachments:
        extended_parts.append(f"Allegati: {summary_attachments}")
    
    extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🤖 Automation: Archiviata automaticamente come spam/sconosciuto")
    
    
    
    
    # Return automation executed response
    return AutomationExecutedResponse(
        message_id=message_id,
        thread_id=thread_id,
        status="automation_executed",
        message="Email spam/sconosciuta archiviata automaticamente",
        result={
            "category": category,
            "subcategory": subcategory,
            "human_response": False,
            "mail_summary": mail_summary,
            "extended_summary": extended_summary
        }
    )


def handle_unrelated_content_node(state):
    """Handle UNRELATED_CONTENT subcategory emails - automated processing."""
    print(f"🔀 [UNRELATED_CONTENT] Processing unrelated content (automated)")
    
    # Extract necessary information from state
    extracted_info = state.get("extracted_info", {})
    message_id = extracted_info.get("message_id")
    thread_id = extracted_info.get("thread_id")
    category = state.get("category")
    subcategory = state.get("subcategory")
    mail_summary = state.get("mail_summary", "")
    summary_attachments = state.get("summary_attachments", "")
    
    # Create extended summary combining mail summary and attachments
    extended_parts = []
    if mail_summary:
        extended_parts.append(f"Contenuto email: {mail_summary}")
    if summary_attachments:
        extended_parts.append(f"Allegati: {summary_attachments}")
    
    extended_summary = " | ".join(extended_parts) if extended_parts else mail_summary
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    print(f"   🤖 Automation: Archiviata automaticamente come contenuto non pertinente")
    
    
    
    
    # Return automation executed response
    return AutomationExecutedResponse(
        message_id=message_id,
        thread_id=thread_id,
        status="automation_executed",
        message="Contenuto non pertinente archiviato automaticamente",
        result={
            "category": category,
            "subcategory": subcategory,
            "human_response": False,
            "mail_summary": mail_summary,
            "extended_summary": extended_summary
        }
    )


def subcategory_router_node(state):
    """Router node for subcategory-specific handling."""
    subcategory = state.get("subcategory", "SPAM_OR_UNKNOWN")
    print(f"🔀 [SUBCATEGORY_ROUTER] Routing to subcategory handler: {subcategory}")
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
            from datetime import datetime
            extended_summary = state.get("extended_summary", "")
            extracted_info = state.get("extracted_info", {})
            sender_email = extracted_info.get("from", "mail not available")
            current_timestamp = datetime.now().isoformat()
            
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
            current_timestamp = datetime.now().isoformat()
            
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
            current_timestamp = datetime.now().isoformat()
            
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
            # CANCEL_APPOINTMENT needs_response is not used
            state["needs_response"] = None
            
            print(f"✅ [READER] Cancellation analysis completed successfully")
            print(f"   🔑 Event code: {cancellation_response.event_code}")
            
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
            
            # Print entity details for debugging
            for entity_type, values in reader_response.key_entities.items():
                if values:
                    print(f"   🏷️ {entity_type}: {len(values)} items")
        
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
        message_id = extracted_info.get("message_id")
        service_id = user_config.get("service_id")
        thread_id = extracted_info.get("thread_id")
        created_by = extracted_info.get("from", "unknown")
        event_type = "APPOINTMENT"  # Default event type
        category = state.get("category", "")
        subcategory = state.get("subcategory", "")
        event_code = state.get("event_code", "")
        
        if not service_id:
            # TODO notification and save to db
            print(f"⚠️ [SCHEDULER] No service_id found in user_config, cannot book appointment")
            return AutomationExecutedResponse(
                message_id=message_id,
                thread_id=thread_id,
                status="automation_executed",
                message=f"Servizio calendario non trovato per evento {event_code}",
                result={
                    "category": category,
                    "subcategory": subcategory,
                    "human_response": True,
                    "mail_summary": mail_summary,
                    "action": "service_not_found"
                }
            )
        
        # Determine if we need to propose slots or book directly TODO migliorare logica -> prompt engineering
        propose_slots = False
        if appointment_date is None:
            propose_slots = True
        else:
            try:
                if isinstance(appointment_date, str) and 'T' in appointment_date:
                    time_part = appointment_date.split('T', 1)[1]
                    hh_mm = ':'.join(time_part.split(':')[:2])  # "hh:mm"
                    propose_slots = (hh_mm == "00:00")
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
        
        # Get current timestamp
        from datetime import datetime
        current_timestamp = datetime.now().isoformat()
        
        # Get appointment details from state (for booking)
        appointment_info = {
            "title_of_event": state.get("appointment_title"),
            "date": state.get("appointment_date"),
            "duration": state.get("appointment_duration", 60),
            "attendees": state.get("appointment_attendees"),
            "place": state.get("appointment_place"),
            "additional_notes": state.get("appointment_notes")
        }
        
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
            language=language
        )
        
        # Update state with scheduling results
        state["appointment_scheduled"] = scheduler_response.scheduled
        state["appointment_overlap"] = scheduler_response.overlap
        state["appointment_event_code"] = scheduler_response.event_code
        state["appointment_proposed_slots"] = scheduler_response.proposed_slots
        
        print(f"✅ [SCHEDULER] Scheduling completed successfully")
        print(f"   ✓ Scheduled: {scheduler_response.scheduled}")
        print(f"   ⚠️ Overlap: {scheduler_response.overlap}")
        print(f"   🔢 Event code: {scheduler_response.event_code}")
        print(f"   📆 Proposed slots: {scheduler_response.proposed_slots}")
        
        return state
        
    except Exception as e:
        print(f"❌ [SCHEDULER] Error in appointment scheduling: {e}")
        # Set default values on error
        state["appointment_scheduled"] = False
        state["appointment_overlap"] = False
        state["appointment_event_code"] = None
        state["appointment_proposed_slots"] = None
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
            return state
        
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
        propose_slots = False
        if new_date is None:
            propose_slots = True
        else:
            try:
                if isinstance(new_date, str) and 'T' in new_date:
                    time_part = new_date.split('T', 1)[1]
                    hh_mm = ':'.join(time_part.split(':')[:2])  # "hh:mm"
                    propose_slots = (hh_mm == "00:00")
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
        
        # Get current timestamp
        current_timestamp = datetime.now().isoformat()
        
        # Get appointment change details from state
        appointment_info = {
            "title_of_event": state.get("change_new_title"),
            "date": state.get("change_new_date"),
            "duration": state.get("change_new_duration"),
            "attendees": state.get("change_new_attendees"),
            "place": state.get("change_new_place"),
            "additional_notes": state.get("change_additional_notes")
        }
        
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
            language=language
        )
        
        # Update state with rescheduling results
        state["appointment_scheduled"] = rescheduler_response.scheduled
        state["appointment_overlap"] = rescheduler_response.overlap
        state["appointment_event_code"] = rescheduler_response.event_code
        state["appointment_proposed_slots"] = rescheduler_response.proposed_slots
        
        print(f"✅ [RESCHEDULER] Rescheduling completed successfully")
        print(f"   ✓ Scheduled: {rescheduler_response.scheduled}")
        print(f"   ⚠️ Overlap: {rescheduler_response.overlap}")
        print(f"   🔢 Event code: {rescheduler_response.event_code}")
        print(f"   📆 Proposed slots: {rescheduler_response.proposed_slots}")
        
        return state
        
    except Exception as e:
        print(f"❌ [RESCHEDULER] Error in appointment rescheduling: {e}")

        # TODO notification and save to db

        return AutomationExecutedResponse(
            message_id=state.get("message_id"),
            thread_id=state.get("thread_id"),
            status="automation_executed",
            message="Errore durante la modifica dell'appuntamento",
            result={
                "category": state.get("category"),
                "subcategory": state.get("subcategory"),
                "human_response": True,
                "mail_summary": state.get("mail_summary"),
                "extended_summary": state.get("extended_summary"),
                "event_code": state.get("change_event_code"),
                "message": "Errore durante la modifica dell'appuntamento"
            }
        )

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
    filtered_body = state.get("email_body", "")
    extended_summary = state.get("extended_summary", "")
    language = state.get("language", "ITA")
    sender_email = extracted_info.get("from", "mail not available")
    
    print(f"   📧 Subject: {extracted_info.get('subject', 'Unknown')[:50]}...")
    
    current_timestamp = datetime.now().isoformat()
    
    print(f"   📖 Reading cancellation request for event_code...")
    cancel_response = llm_client.read_cancellation_request(
        filtered_body,
        mail_summary,
        extended_summary,
        current_timestamp,
        sender_email,
        language
    )
    
    # Extract event_code from response
    event_code = cancel_response.event_code

    if event_code is None or (isinstance(event_code, str) and len(event_code) != 6):
        print(f"⚠️ [CANCELLATION] Invalid event_code: {event_code}")
        return state
    
    # Check if event_code is present
    if event_code and isinstance(event_code, str) and len(event_code) == 6:
        print(f"   🔑 Event code found: {event_code}")
        
        try:
            print(f"   🔍 Searching for event {event_code} in database...")

            event_response = get_scheduled_event_by_code(event_code)
            
            if not event_response:
                print(f"   ⚠️ Event {event_code} not found in database")
                
                #TODO: Send a notification and save in DB

                # Return automation response indicating event not found
                return AutomationExecutedResponse(
                    message_id=message_id,
                    thread_id=thread_id,
                    status="automation_executed",
                    message=f"Codice evento {event_code} non trovato nel sistema",
                    result={
                        "category": category,
                        "subcategory": subcategory,
                        "human_response": True,
                        "mail_summary": mail_summary,
                        "event_code": event_code,
                        "action": "event_not_found"
                    }
                )
            
            event_data = event_response
            event_automation_id = event_data.get("event_automation_id")
            service_id = event_data.get("service_id")
            calendar_event_id = event_data.get("provider_event_id")
            
            print(f"   ✅ Event found in database: event_automation_id={event_automation_id}")
            
            # Get calendar service data to determine provider and token
            service_data = get_calendar_service_data(service_id)
            
            if not service_data:
                #TODO: Send a notification and save in DB

                print(f"   ❌ Calendar service data not found for service_id: {service_id}")
                return AutomationExecutedResponse(
                    message_id=message_id,
                    thread_id=thread_id,
                    status="automation_executed",
                    message=f"Servizio calendario non trovato per evento {event_code}",
                    result={
                        "category": category,
                        "subcategory": subcategory,
                        "human_response": True,
                        "mail_summary": mail_summary,
                        "event_code": event_code,
                        "action": "service_not_found"
                    }
                )
            
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
            
            if db_delete_response:
                print(f"   ✅ Event {event_code} successfully deleted")
                return state
            else:
                #TODO: Send a notification and save in DB
                print(f"   ❌ Failed to delete event {event_code}")
                return AutomationExecutedResponse(
                    message_id=message_id,
                    thread_id=thread_id,
                    status="automation_executed",
                    message=f"Errore durante la cancellazione dell'appuntamento {event_code}",
                    result={
                        "category": category,
                        "subcategory": subcategory,
                        "human_response": True,
                        "mail_summary": mail_summary,
                        "event_code": event_code,
                        "action": "deletion_failed"
                    }
                )
                
        except Exception as e:
            #TODO: Send a notification and save in DB
            print(f"   ❌ Error processing cancellation: {e}")
            return AutomationExecutedResponse(
                message_id=message_id,
                thread_id=thread_id,
                status="automation_executed",
                message=f"Errore durante la cancellazione: {str(e)}",
                result={
                    "category": category,
                    "subcategory": subcategory,
                    "human_response": True,
                    "mail_summary": mail_summary,
                    "event_code": event_code,
                    "action": "error",
                    "error": str(e)
                }
            )
    else:
        #TODO: Send a notification and save in DB
        print(f"   ⚠️ No event code found in email")
        return AutomationExecutedResponse(
            message_id=message_id,
            thread_id=thread_id,
            status="automation_executed",
            message="Richiesta di cancellazione senza codice evento - richiede attenzione",
            result={
                "category": category,
                "subcategory": subcategory,
                "human_response": True,
                "mail_summary": mail_summary,
                "action": "no_event_code"
            }
        )

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
        
        # Step 2: Gestione caso information vuota o non presente
        if not company_information:
            print(f"⚠️ [EXTRACTOR_COMPANY_INFO] Company information not available - sending notification")
            
            # Salva notifica nel database
            insert_notification_sync(
                email=box_email,
                notification_type="INFORMATION_NOT_PRESENT",
                message_id=message_id,
                text="Company information not available in database"
            )
            
            # Invia notifica via webhook
            filtered_body = state.get('email_body', '')
            summary_attachments = state.get('summary_attachments')
            
            send_information_not_present_notification(
                sender_email=from_email,
                box_email=box_email,
                subject=subject,
                body=filtered_body,
                summary_attachment=summary_attachments
            )
            
            print(f"✅ [EXTRACTOR_COMPANY_INFO] Notification sent - ending workflow with human response required")
            
            # Ritorna AutomationExecutedResponse con human_response = True
            return AutomationExecutedResponse(
                message_id=message_id,
                thread_id=thread_id,
                status="automation_executed",
                message="Company information not available - human response required",
                result={
                    "extended_summary": state.get('extended_summary'),
                    "human_response": True,
                    "notification_sent": True,
                    "notification_type": "INFORMATION_NOT_PRESENT"
                }
            )
        
        # Step 3: Estrai informazioni rilevanti tramite LLM
        extended_summary = state.get('extended_summary', '')
        mail_summary = state.get('mail_summary', '')
        summary_attachments = state.get('summary_attachments', '')
        key_entities = state.get('key_entities', {})
        language = state.get('language', 'ITA')
        
        print(f"   📝 Extended summary length: {len(extended_summary)}")
        print(f"   📝 Mail summary length: {len(mail_summary)}")
        print(f"   📎 Has attachment summary: {bool(summary_attachments)}")
        print(f"   🔑 Key entities: {len(key_entities)} items")
        
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

        # DEBUG
        print(f"✅ [EXTRACTOR_COMPANY_INFO] Company information extracted successfully")
        print(f"   📝 Chunked company informations extracted:\n {extraction_result.chunked_company_informations} ")
        
        return state
        
    except Exception as e:
        print(f"❌ [EXTRACTOR_COMPANY_INFO] Error extracting company information: {str(e)}")
        # In caso di errore, ritorna stato con dizionario vuoto
        from db_client import insert_notification_sync
        
        # Invia notifica via webhook
        state['chunked_company_informations'] = {}
        
        extracted_info = state.get('extracted_info', {})
        box_email = extracted_info.get('box_email', 'unknown')
        message_id = extracted_info.get('message_id', 'unknown')
        thread_id = extracted_info.get('thread_id', 'unknown')
        
        # Salva notifica nel database
        insert_notification_sync(
            email=box_email,
            notification_type="INFORMATION_NOT_PRESENT",
            message_id=message_id,
            text=f"Error extracting company information: {str(e)}"
        )
        
        send_information_not_present_notification(
            sender_email=extracted_info.get('from', 'unknown'),
            box_email=extracted_info.get('box_email', 'unknown'),
            subject=extracted_info.get('subject', 'No Subject'),
            body=state.get('email_body', ''),
            summary_attachment=state.get('summary_attachments', '')
        )
        return state

def writer_node(state):
    """
    Write company information to database.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with company information or AutomationExecutedResponse if writing fails
    """
    ## TODO
    
    return state

def reviewer_node(state):
    """
    Review company information.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with company information or AutomationExecutedResponse if review fails
    """
    ## TODO
    
    return state

def sender_node(state):
    """
    Send company information to user.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with company information or AutomationExecutedResponse if sending fails
    """
    ## TODO
    
    return state

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
