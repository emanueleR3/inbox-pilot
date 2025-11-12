"""
Core workflow nodes for email processing.
"""

import os
from langgraph.graph import END
from .config import NodeNames
from ..llm.client import llm_client
from ..models.llm_responses import DangerousEmailDetected, LowConfidenceClassification

# Import db_client for user configuration and notifications
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
from db_client import get_user_configuration_sync, get_default_configuration, insert_notification_sync, get_email_attachments_sync

# Import attachment extractor service
from ..services.attachment_extractor import attachment_extractor
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
