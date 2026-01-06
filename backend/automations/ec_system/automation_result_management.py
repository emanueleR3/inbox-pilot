from db_client import (
    insert_notification_sync,
    save_ai_generated_email,
    get_subscription_service_id_by_email,
    update_thread,
    get_email_service_data,
    insert_new_mail_in_history_thread,
    get_calendar_service_data
)
import os
import requests
import base64
import uuid
import html
from .services.notification_client import (
    send_high_priority_notification, 
    send_low_confidence_notification,
    send_event_invite_notification,
    send_information_not_present_notification,
    send_event_followup_notification,
    send_appointment_not_scheduled_notification,
    send_no_available_slots_notification,
    send_appointment_not_rescheduled_notification,
    send_event_code_not_found_notification,
    send_calendar_service_not_found_notification,
    send_event_deletion_failed_notification,
    send_email_not_sent_notification,
    send_low_confidence_writer_notification,
    send_no_calendar_provided_notification
)
from .utils.utils import (
    get_google_calendar_timezone,
    get_microsoft_calendar_timezone
)
from models import ThreadStatus, EmailOutcome
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()


def _generate_ics_content(event_details: dict) -> str:
    """
    Generate an ICS (iCalendar) file content from event details.
    
    Args:
        event_details: Dictionary containing event information:
            - title: Event title
            - start_time: Start time in ISO format
            - end_time: End time in ISO format
            - location: Event location (optional)
            - description: Event description (optional)
            - attendees: List of attendee emails (optional)
            - event_code: Unique event code
            - timezone: Event timezone
            
    Returns:
        ICS file content as string
    """
    try:
        title = event_details.get('title', 'Appuntamento')
        start_time_str = event_details.get('start_time')
        end_time_str = event_details.get('end_time')
        location = event_details.get('location', '')
        description = event_details.get('description', '')
        attendees = event_details.get('attendees', [])
        event_code = event_details.get('event_code', '')
        event_timezone = event_details.get('timezone', 'Europe/Rome')
        
        # Parse times
        start_dt = datetime.fromisoformat(start_time_str)
        end_dt = datetime.fromisoformat(end_time_str)
        
        # Format times for ICS (UTC format)
        # Convert to UTC for DTSTART/DTEND
        if start_dt.tzinfo is not None:
            start_utc = start_dt.astimezone(timezone.utc)
            end_utc = end_dt.astimezone(timezone.utc)
        else:
            # If naive, assume it's in the specified timezone
            tz = ZoneInfo(event_timezone)
            start_utc = start_dt.replace(tzinfo=tz).astimezone(timezone.utc)
            end_utc = end_dt.replace(tzinfo=tz).astimezone(timezone.utc)
        
        # Format as YYYYMMDDTHHMMSSZ
        start_ics = start_utc.strftime('%Y%m%dT%H%M%SZ')
        end_ics = end_utc.strftime('%Y%m%dT%H%M%SZ')
        
        # Create timestamp for DTSTAMP
        now_utc = datetime.now(timezone.utc)
        dtstamp = now_utc.strftime('%Y%m%dT%H%M%SZ')
        
        # Generate unique UID
        uid = f"{event_code}-{uuid.uuid4()}@corretto.ai"
        
        # Escape special characters for ICS
        def escape_ics(text):
            if not text:
                return ''
            return text.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')
        
        # Build ICS content
        ics_lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//Corretto AI//Email Assistant//IT',
            'CALSCALE:GREGORIAN',
            'METHOD:REQUEST',
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'DTSTAMP:{dtstamp}',
            f'DTSTART:{start_ics}',
            f'DTEND:{end_ics}',
            f'SUMMARY:{escape_ics(title)}',
        ]
        
        if location:
            ics_lines.append(f'LOCATION:{escape_ics(location)}')
        
        if description:
            ics_lines.append(f'DESCRIPTION:{escape_ics(description)}')
        
        # Add attendees
        for attendee in attendees:
            if attendee and '@' in attendee:
                ics_lines.append(f'ATTENDEE;RSVP=TRUE:mailto:{attendee}')
        
        # Add event code as custom property
        if event_code:
            ics_lines.append(f'X-CORRETTO-EVENT-CODE:{event_code}')
        
        ics_lines.extend([
            'STATUS:CONFIRMED',
            'SEQUENCE:0',
            'END:VEVENT',
            'END:VCALENDAR'
        ])
        
        return '\r\n'.join(ics_lines)
        
    except Exception as e:
        print(f"❌ [ICS] Error generating ICS content: {e}")
        return None


def _create_ics_attachment(event_details: dict) -> dict:
    """
    Create an ICS attachment dictionary for email sending.
    
    Args:
        event_details: Event details dictionary
        
    Returns:
        Attachment dictionary with filename, content (base64), and content_type
        Returns None if ICS generation fails
    """
    try:
        ics_content = _generate_ics_content(event_details)
        if not ics_content:
            return None
        
        # Encode to base64
        ics_bytes = ics_content.encode('utf-8')
        ics_base64 = base64.b64encode(ics_bytes).decode('utf-8')
        
        return {
            'filename': 'invite.ics',
            'content': ics_base64,
            'content_type': 'text/calendar; method=REQUEST'
        }
        
    except Exception as e:
        print(f"❌ [ICS] Error creating ICS attachment: {e}")
        return None


def _get_ai_disclaimer() -> str:
    """
    Returns a professional, minimal AI-generated email disclaimer banner.
    This should be prepended to the body of AI-generated emails.
    """
    return """<div style="border-left:3px solid #6366f1;background:linear-gradient(to right,#f8fafc,#ffffff);padding:12px 16px;margin:0 0 20px 0;border-radius:0 6px 6px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
    <p style="margin:0;font-size:12px;color:#64748b;line-height:1.5">
        <span style="color:#6366f1;font-weight:600">⚡ AI Generated</span>
        <span style="color:#94a3b8;margin:0 6px">•</span>
        <span>Questa email è stata generata automaticamente da un sistema AI in base ai contenuti della conversazione.</span>
    </p>
</div>
"""


def _convert_plain_text_to_html(text: str) -> str:
    """
    Converts plain text email content to HTML format.
    Preserves line breaks and basic formatting.
    
    Args:
        text: Plain text content
        
    Returns:
        HTML formatted content
    """
    
    # Escape HTML special characters to prevent injection
    escaped_text = html.escape(text)
    
    # Convert line breaks to <br> tags
    # Handle both \r\n (Windows) and \n (Unix) line endings
    html_text = escaped_text.replace('\r\n', '<br>').replace('\n', '<br>')
    
    # Wrap in a styled div for consistent formatting
    return f'<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;font-size:14px;line-height:1.6;color:#333333">{html_text}</div>'


def _wrap_body_with_disclaimer(body: str) -> str:
    """
    Wraps an email body with the AI disclaimer at the top.
    Converts plain text body to HTML format for proper rendering.
    
    Args:
        body: The original email body content (plain text or HTML)
        
    Returns:
        Full HTML email with disclaimer prepended
    """
    disclaimer = _get_ai_disclaimer()
    
    # Check if body is already HTML
    stripped_body = body.strip()
    is_html = (
        stripped_body.startswith('<') and 
        (stripped_body.startswith('<!DOCTYPE') or 
         stripped_body.startswith('<html') or 
         stripped_body.startswith('<div') or
         stripped_body.startswith('<p'))
    )
    
    if is_html:
        # Body is already HTML, just prepend disclaimer
        html_body = body
    else:
        # Convert plain text to HTML
        html_body = _convert_plain_text_to_html(body)
    
    # Wrap everything in a complete HTML structure
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:20px;background-color:#ffffff">
{disclaimer}
{html_body}
</body>
</html>"""
    
    return full_html


def _get_user_timezone(box_email: str) -> str:
    """
    Get the user's timezone from their calendar provider settings.
    
    Args:
        box_email: The user's email address
        
    Returns:
        Timezone string (e.g., "Europe/Rome"). Defaults to "Europe/Rome" if not found.
    """
    try:
        # Get service_id from email
        service_id = get_subscription_service_id_by_email(box_email)
        if not service_id:
            print(f"⚠️ [TIMEZONE] No service_id found for {box_email}, using default Europe/Rome")
            return "Europe/Rome"
        
        # Get calendar service data
        calendar_data = get_calendar_service_data(service_id)
        if not calendar_data:
            print(f"⚠️ [TIMEZONE] No calendar data found for service_id {service_id}, using default Europe/Rome")
            return "Europe/Rome"
        
        calendar_provider = calendar_data.get("calendar_provider")
        access_token = calendar_data.get("access_token")
        
        if not access_token:
            print(f"⚠️ [TIMEZONE] No access token found, using default Europe/Rome")
            return "Europe/Rome"
        
        # Get timezone based on provider
        if calendar_provider == "google":
            user_timezone = get_google_calendar_timezone(access_token)
        elif calendar_provider == "microsoft":
            user_timezone = get_microsoft_calendar_timezone(access_token, box_email)
        else:
            print(f"⚠️ [TIMEZONE] Unknown calendar provider: {calendar_provider}, using default Europe/Rome")
            return "Europe/Rome"
        
        print(f"🌍 [TIMEZONE] Retrieved timezone for {box_email}: {user_timezone}")
        return user_timezone
        
    except Exception as e:
        print(f"❌ [TIMEZONE] Error getting timezone for {box_email}: {e}")
        return "Europe/Rome"


def _get_timestamp_in_user_timezone(box_email: str) -> str:
    """
    Get the current timestamp converted to the user's timezone.
    
    Args:
        box_email: The user's email address
        
    Returns:
        ISO format timestamp in user's local timezone
    """
    try:
        user_timezone = _get_user_timezone(box_email)
        now_utc = datetime.now(timezone.utc)
        target_tz = ZoneInfo(user_timezone)
        now_local = now_utc.astimezone(target_tz)
        return now_local.isoformat()
    except Exception as e:
        print(f"❌ [TIMESTAMP] Error converting timestamp for {box_email}: {e}")
        # Fallback to UTC
        return datetime.now(timezone.utc).isoformat()


def _create_draft_in_provider(
    box_email: str,
    sender_email: str,
    subject: str,
    response_body: str,
    message_id: str = None,
    reply_to_id: str = None,
    original_thread_id: str = None,
    microsoft_message_id: str = None,
    scheduled_event_details: dict = None
) -> tuple[bool, str]:
    """
    Create a draft email in the user's email provider (Gmail/Microsoft/IMAP).
    
    Args:
        box_email: User's mailbox email
        sender_email: Email to reply to
        subject: Email subject
        response_body: Body content of the draft
        message_id: Message ID for threading
        reply_to_id: Reply-to message ID
        original_thread_id: Original thread ID for Gmail
        microsoft_message_id: Microsoft Graph message ID for replies
        scheduled_event_details: Event details for ICS attachment (optional)
        
    Returns:
        Tuple of (success: bool, draft_id: str or None)
    """
    # Skip if no body to draft
    if not response_body or not response_body.strip():
        print(f"⚠️ [DRAFT] No response body to create draft - skipping draft creation")
        return False, None
    
    try:
        # Get email service data
        email_service_data = get_email_service_data(box_email)
        if not email_service_data:
            print(f"❌ [DRAFT] No email service data found for {box_email}")
            return False, None
        
        provider = email_service_data.get("email_provider")
        if not provider:
            print(f"❌ [DRAFT] No email provider configured for {box_email}")
            return False, None
        
        # Add AI disclaimer to the response body
        response_body_with_disclaimer = _wrap_body_with_disclaimer(response_body)
        
        # Prepare payload
        payload = {
            "email": sender_email,
            "subject": subject,
            "body": response_body_with_disclaimer,
        }
        
        # Generate ICS attachment if event was scheduled/rescheduled
        if scheduled_event_details:
            ics_attachment = _create_ics_attachment(scheduled_event_details)
            if ics_attachment:
                payload["attachments"] = [ics_attachment]
                print(f"📎 [DRAFT] ICS attachment generated for event code: {scheduled_event_details.get('event_code')}")
        
        senders_url = os.getenv("SENDERS_URL")
        endpoint = ""
        
        if provider == "google":
            endpoint = f"{senders_url}/send-email/draft-gmail"
            payload["hashed_access_token"] = email_service_data.get("hashed_access_token")
            payload["original_thread_id"] = original_thread_id
            payload["message_id"] = message_id
        elif provider == "microsoft":
            endpoint = f"{senders_url}/send-email/draft-microsoft"
            payload["hashed_access_token"] = email_service_data.get("hashed_access_token")
            payload["message_id"] = microsoft_message_id
        elif provider == "imap":
            endpoint = f"{senders_url}/send-email/draft-imap"
            imap_server = email_service_data.get("imap_server")
            if not imap_server:
                smtp_server = email_service_data.get("smtp_server", "")
                imap_server = smtp_server.replace("smtp.", "imap.") if smtp_server.startswith("smtp.") else smtp_server
            imap_port = email_service_data.get("imap_port") or 993
            payload["imap_server"] = imap_server
            payload["imap_port"] = imap_port
            payload["imap_email"] = box_email
            payload["password"] = email_service_data.get("hashed_password")
            payload["reply_to_id"] = reply_to_id
            payload["message_id"] = message_id
        else:
            print(f"❌ [DRAFT] Unknown email provider: {provider}")
            return False, None
        
        # Send request
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        
        result = response.json()
        draft_id = result.get("draft_id") or result.get("message_id")
        
        if not result.get("success"):
            print(f"❌ [DRAFT] Draft creation failed: {result.get('message')}")
            return False, None
        
        print(f"✅ [DRAFT] Draft created successfully via {provider}, draft_id: {draft_id}")
        return True, draft_id
        
    except Exception as e:
        print(f"❌ [DRAFT] Error creating draft: {e}")
        return False, None


def process_automation_result(workflow_result: dict):
    """
    Process the results of the automation workflow.
    """

    status = workflow_result.get("status", "unknown")

    # ======= AUTOMATION DISABLED CHECK ======= ✅
    if status == "AUTOMATION_DISABLED":
        print(f"⚠️ [WORKFLOW] Automation is disabled. No processing to be done.")
        return
    elif status == "FAILED":
        print(f"❌ [WORKFLOW] Workflow execution failed - Details: {workflow_result.get('error', 'No details provided')}")
        return

    # variables
    human_response = workflow_result.get("human_response", None)
    extracted_info = workflow_result.get('extracted_info', {})
    box_email = extracted_info.get('box_email', 'unknown')
    message_id = extracted_info.get('message_id', 'unknown')
    email_id = workflow_result.get("email_id", None)  # Email UUID from emails table for notifications/events
    sender_email = extracted_info.get("from", "unknown")
    subject = extracted_info.get("subject", "No subject")
    thread_id = extracted_info.get("thread_id", None)
    reply_to_id = extracted_info.get("reply_to_id", None)
    summary = workflow_result.get("mail_summary", "")
    extended_summary = workflow_result.get("extended_summary", None)
    cc_emails = extracted_info.get("cc", "")
    has_attachments = extracted_info.get("has_attachments", False)
    priority_score = workflow_result.get("priority_score", 0)
    response_body = workflow_result.get("written_email_body", "")
    category = workflow_result.get("category", "")
    subcategory = workflow_result.get("subcategory", "")
    email_body = workflow_result.get("email_body", "")
    summary_attachments = workflow_result.get("summary_attachments", None)
    now_tz = datetime.now(timezone.utc).isoformat()
    original_thread_id = workflow_result.get("original_thread_id", None)
    microsoft_message_id = workflow_result.get("microsoft_message_id", None)  # Microsoft Graph internal ID for replies
    scheduled_event_details = workflow_result.get("scheduled_event_details", None)  # Event details for ICS attachment

    # Get timestamp in user's timezone for notification formatting
    notification_timestamp = _get_timestamp_in_user_timezone(box_email)

    # ======= SUMMARIZER ONLY CHECK ======= ✅
    if workflow_result.get("summarizer_only", False):   
        print(f"⚠️ [WORKFLOW] Summarizer only. - Saving summary and extended summary")
        if not thread_id:
            print(f"❌ [WORKFLOW] No thread_id found in workflow result")
            return

        thread_data = {
            "summary": summary,
            "extended_summary": extended_summary,
            "cc_emails": cc_emails
        }

        try:
            update_thread(thread_id, thread_data)
        except Exception as e:
            print(f"❌ [WORKFLOW] Error updating thread: {e}")
        return    
    
    # ======= DANGEROUS EMAIL CHECK ======= ✅
    if workflow_result.get("dangerous_email", False):
        print(f"🚨 [WORKFLOW] DANGEROUS EMAIL DETECTED!")

        thread_data = {
            "human_response": True,
            "status": ThreadStatus.DANGEROUS_EMAIL.value
        }

        try:
            update_thread(thread_id, thread_data)
        except Exception as e:
            print(f"❌ [WORKFLOW] Error updating thread: {e}")

        
        # Insert notification in database
        try:
            notification_success = insert_notification_sync(
                email=box_email,
                notification_type="MAIL_NOT_PERMITTED",
                email_id=email_id,
                text=None  # No text as requested
            )
            
            if not notification_success:
                print(f"❌ [GUARDRAIL] Failed to insert notification for {box_email}")
                
        except Exception as e:
            print(f"❌ [GUARDRAIL] Error inserting notification: {e}")
        
        return
    
    # ======= LOW CONFIDENCE CLASSIFICATION CHECK ======= ✅
    if workflow_result.get("low_confidence_classification", False):
        print(f"⚠️ [WORKFLOW] LOW CONFIDENCE CLASSIFICATION DETECTED!")
        
        thread_data = {
            "category": category,
            "summary": summary,
            "extended_summary": extended_summary,
            "human_response": True,
            "status": ThreadStatus.LOW_CONFIDENCE_CLASSIFICATION.value
        }

        try:
            update_thread(thread_id, thread_data)
        except Exception as e:
            print(f"❌ [WORKFLOW] Error updating thread: {e}")
        
        # Insert notification in database
        try:
            notification_success = insert_notification_sync(
                email=box_email,
                notification_type="LOW_CONFIDENCE_CLASSIFICATION_MAIL",
                email_id=email_id,
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
            body=workflow_result.get("email_body", ""),
            summary_attachment=workflow_result.get("summary_attachments"),
            timestamp=notification_timestamp
        )
        return
    
    # ======= HIGH PRIORITY EMAIL CHECK ======= ✅
    if workflow_result.get("high_priority_email", False):
        print(f"🔥 [WORKFLOW] HIGH PRIORITY EMAIL DETECTED!")
        
        service_id = None
        try:
            service_id = get_subscription_service_id_by_email(box_email)
        except Exception as e:
            print(f"❌ [WORKFLOW] Error getting service_id: {e}")

        thread_data = {
            "category": category,
            "subcategory": subcategory,
            "summary": summary,
            "extended_summary": extended_summary,
            "human_response": True,
            "status": ThreadStatus.HIGH_PRIORITY.value
        }

        try:
            update_thread(thread_id, thread_data)

            # Create draft in provider if response_body is available
            draft_created = False
            draft_id = None
            if response_body and response_body.strip():
                draft_created, draft_id = _create_draft_in_provider(
                    box_email=box_email,
                    sender_email=sender_email,
                    subject=subject,
                    response_body=response_body,
                    email_id=email_id,
                    reply_to_id=reply_to_id,
                    original_thread_id=original_thread_id,
                    microsoft_message_id=microsoft_message_id,
                    scheduled_event_details=scheduled_event_details
                )
                
                # Save AI generated email record
                ai_email_data = { 
                    "thread_id": thread_id,
                    "message_id": draft_id,
                    "response_at_id": message_id,
                    "processed_at": now_tz,
                    "duration": 0, #TODO calculate duration
                    "priority_score": priority_score,
                    "body": response_body,
                    "service_id": service_id,
                    "outcome": EmailOutcome.DRAFT.value
                }
                save_ai_generated_email(ai_email_data)
            else:
                print(f"⚠️ [HIGH_PRIORITY] No response body available - skipping draft creation")

        except Exception as e:
            print(f"❌ [WORKFLOW] Error saving AI generated email: {e}")

        # Insert notification in database
        try:
            notification_success = insert_notification_sync(
                email=box_email,
                notification_type="HIGH_PRIORITY_MAIL",
                email_id=email_id,
                text=None
            )
            
            if not notification_success:
                print(f"❌ [PRIORITY_CONTROLLER] Failed to insert notification for {box_email}")
                
        except Exception as e:
            print(f"❌ [PRIORITY_CONTROLLER] Error inserting notification: {e}")
        
        # Send notification webhook for high priority email
        try:
            send_high_priority_notification(
                sender_email=sender_email,
                box_email=box_email,
                subject=subject,
                body=email_body,
                summary_attachment=summary_attachments,
                timestamp=notification_timestamp
            )
        except Exception as e:
            print(f"❌ [PRIORITY_CONTROLLER] Error sending high priority notification: {e}")
        
        return

    # ======= NO TASKS (NO REPLY) CHECK =======
    # If TASKS_EXTRACTOR produced an empty task list, the workflow ends early.
    # We still need to persist the computed fields on the thread.
    list_of_tasks = workflow_result.get("list_of_tasks")
    if isinstance(list_of_tasks, list) and len(list_of_tasks) == 0:
        if not thread_id:
            print(f"❌ [WORKFLOW] No thread_id found in workflow result (no tasks)")
            return

        # Normalize enum subcategory to string for DB consistency
        subcategory_value = subcategory.value if hasattr(subcategory, "value") else subcategory

        thread_data = {
            "category": category,
            "subcategory": subcategory_value,
            "summary": summary,
            "extended_summary": extended_summary,
            "status": ThreadStatus.PROCESSED.value,
        }

        try:
            update_thread(thread_id, thread_data)
            print(f"✅ [WORKFLOW] No tasks extracted - thread updated as PROCESSED")
        except Exception as e:
            print(f"❌ [WORKFLOW] Error updating thread (no tasks): {e}")

        return
    
    # ======= AUTOMATION EXECUTED CHECK =======
    if workflow_result.get("automation_executed", False):
        print(f"✅ [WORKFLOW] AUTOMATION EXECUTED SUCCESSFULLY!")

        if human_response:
            box_email = box_email
            message_id = message_id
            sender_email = sender_email
            subject = subject


            # CASE - EVENT_INVITE with category INFORMATION_PROVIDED/CALENDAR_EVENT ⚠️
            if status == "EVENT_INVITE_HUMAN_RESPONSE_REQUIRED":
                print(f"⚠️ [WORKFLOW] EVENT INVITE DETECTED - SENDING NOTIFICATION")

                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "human_response": True,
                    "status": ThreadStatus.HUMAN_REVIEW.value
                }

                # TODO salvare la bozza in DRAFT

                try:
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error updating thread: {e}")

                try:
                    notification_success = insert_notification_sync(
                        email=box_email,
                        notification_type="EVENT_INVITE_MAIL",
                        email_id=email_id,
                        text=None
                    )

                    if not notification_success:
                        print(f"❌ [EVENT_INVITE] Failed to insert notification for {box_email}")

                except Exception as e:
                    print(f"❌ [EVENT_INVITE] Error inserting notification: {e}")

                send_event_invite_notification(
                    sender_email=sender_email,
                    box_email=box_email,
                    subject=subject,
                    body=email_body,
                    summary_attachment=summary_attachments,
                    timestamp=notification_timestamp
                )
                return

            # CASE - NO_CALENDAR_PROVIDED ✅
            if status == "NO_CALENDAR_PROVIDED":
                print(f"⚠️ [WORKFLOW] NO CALENDAR PROVIDED - SENDING NOTIFICATION")

                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "human_response": True,
                    "status": ThreadStatus.HUMAN_REVIEW.value
                }

                try:
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error updating thread: {e}")

                try:
                    notification_success = insert_notification_sync(
                        email=box_email,
                        notification_type="NO_CALENDAR_PROVIDED",
                        email_id=email_id,
                        text=None
                    )

                    if not notification_success:
                        print(f"❌ [NO_CALENDAR_PROVIDED] Failed to insert notification for {box_email}")

                except Exception as e:
                    print(f"❌ [NO_CALENDAR_PROVIDED] Error inserting notification: {e}")

                send_no_calendar_provided_notification(
                    sender_email=sender_email,
                    box_email=box_email,
                    subject=subject,
                    body=email_body,
                    summary_attachment=summary_attachments,
                    timestamp=notification_timestamp
                )
                return

            # CASE - COMPANY_INFO_EXTRACTION_FAILED ✅
            if status == "COMPANY_INFO_EXTRACTION_FAILED":
                print(f"⚠️ [WORKFLOW] COMPANY INFO EXTRACTION FAILED - SENDING NOTIFICATION")

                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "human_response": True,
                    "status": ThreadStatus.HUMAN_REVIEW.value
                }

                try:
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error updating thread: {e}")

                insert_notification_sync(
                    email=box_email,
                    notification_type="INFORMATION_NOT_PRESENT",
                    email_id=email_id,
                    text=f"Error extracting company information: {str(e)}"
                )

                send_information_not_present_notification(
                    sender_email=sender_email,
                    box_email=box_email,
                    subject=subject,
                    body=email_body,
                    summary_attachment=summary_attachments,
                    timestamp=notification_timestamp
                )
                return
            
            # CASE - EVENT_FOLLOWUP with needs response ⚠️
            if status == "EVENT_FOLLOWUP_HUMAN_RESPONSE_REQUIRED":
                print(f"⚠️ [WORKFLOW] EVENT FOLLOW-UP DETECTED - SENDING NOTIFICATION")

                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "human_response": True,
                    "status": ThreadStatus.HUMAN_REVIEW.value
                }

                # TODO salvare la bozza in DRAFT

                try:
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error updating thread: {e}")

                try:
                    notification_success = insert_notification_sync(
                        email=box_email,
                        notification_type="EVENT_FOLLOWUP_MAIL",
                        email_id=email_id,
                        text=None
                    )
                    
                    if not notification_success:
                        print(f"❌ [SCHEDULER] Failed to insert notification for {box_email}")
                        
                except Exception as e:
                    print(f"❌ [SCHEDULER] Error inserting notification: {e}")

                send_event_followup_notification(
                    sender_email=sender_email,
                    box_email=box_email,
                    subject=subject,
                    body=email_body,
                    summary_attachment=summary_attachments,
                    timestamp=notification_timestamp
                )
            
            # CASE - NO AVAILABLE SLOTS ✅
            if status == "NO_AVAILABLE_SLOTS":
                print(f"ℹ️ [WORKFLOW] No available slots for event scheduling.")

                subcategory = extracted_info.get("subcategory", "")
                notification_type = None
                if subcategory == "REQUEST_APPOINTMENT":
                    notification_type = "NO_AVAILABLE_SLOTS_REQUEST_APPOINTMENT_MAIL"
                else:
                    notification_type = "NO_AVAILABLE_SLOTS_RESCHEDULE_APPOINTMENT_MAIL"

                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "human_response": True,
                    "status": ThreadStatus.HUMAN_REVIEW.value
                }

                try:
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error updating thread: {e}")

                try:
                    notification_success = insert_notification_sync(
                        email=box_email,
                        notification_type=notification_type,
                        email_id=email_id,
                        text=None
                    )
                    
                    if not notification_success:
                        print(f"❌ [SCHEDULER] Failed to insert notification for {box_email}")
                        
                except Exception as e:
                    print(f"❌ [SCHEDULER] Error inserting notification: {e}")

                send_no_available_slots_notification(
                    sender_email=sender_email,
                    box_email=box_email,
                    subject=subject,
                    body=email_body,
                    summary_attachment=summary_attachments,
                    timestamp=notification_timestamp
                )
                return

            # CASE - APPOINTMENT NOT SCHEDULED ✅
            if status == "APPOINTMENT_NOT_SCHEDULED":
                print(f"ℹ️ [WORKFLOW] Appointment could not be scheduled.")

                subcategory = extracted_info.get("subcategory", "")
                if subcategory == "REQUEST_APPOINTMENT":
                    notification_type = "APPOINTMENT_NOT_SCHEDULED_MAIL"
                else:
                    notification_type = "APPOINTMENT_NOT_RESCHEDULED_MAIL"

                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "human_response": True,
                    "status": ThreadStatus.HUMAN_REVIEW.value
                }

                try:
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error updating thread: {e}")

                try:
                    notification_success = insert_notification_sync(
                        email=box_email,
                        notification_type=notification_type,
                        email_id=email_id,
                        text=None
                    )
                    
                    if not notification_success:
                        print(f"❌ [SCHEDULER] Failed to insert notification for {box_email}")
                        
                except Exception as e:
                    print(f"❌ [SCHEDULER] Error inserting notification: {e}")

                if subcategory == "REQUEST_APPOINTMENT":
                    send_appointment_not_scheduled_notification(
                        sender_email=sender_email,
                        box_email=box_email,
                        subject=subject,
                        body=email_body,
                        summary_attachment=summary_attachments,
                        timestamp=notification_timestamp
                    )
                else:
                    send_appointment_not_rescheduled_notification(
                        sender_email=sender_email,
                        box_email=box_email,
                        subject=subject,
                        body=email_body,
                        summary_attachment=summary_attachments,
                        timestamp=notification_timestamp
                    )

                return
            
            # CASE - EVENT CODE NOT FOUND ✅
            if status == "EVENT_CODE_NOT_FOUND":
                print(f"ℹ️ [WORKFLOW] Event code not found in database - sending notification.")

                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "human_response": True,
                    "status": ThreadStatus.HUMAN_REVIEW.value
                }

                try:
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error updating thread: {e}")

                try:
                    notification_success = insert_notification_sync(
                        email=box_email,
                        notification_type="EVENT_CODE_NOT_FOUND",
                        email_id=email_id,
                        text=None
                    )
                    
                    if not notification_success:
                        print(f"❌ [SCHEDULER] Failed to insert notification for {box_email}")
                        
                except Exception as e:
                    print(f"❌ [SCHEDULER] Error inserting notification: {e}")

                send_event_code_not_found_notification(
                    sender_email=sender_email,
                    box_email=box_email,
                    subject=subject,
                    body=email_body,
                    summary_attachment=summary_attachments,
                    timestamp=notification_timestamp
                )
                return
            
            # CASE - CALENDAR SERVICE NOT FOUND ✅
            if status == "CALENDAR_SERVICE_NOT_FOUND":
                print(f"ℹ️ [WORKFLOW] Calendar service not found for user - sending notification.")

                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "human_response": True,
                    "status": ThreadStatus.HUMAN_REVIEW.value
                }

                try:
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error updating thread: {e}")

                try:
                    notification_success = insert_notification_sync(
                        email=box_email,
                        notification_type="CALENDAR_SERVICE_NOT_FOUND",
                        email_id=email_id,
                        text=None
                    )
                    
                    if not notification_success:
                        print(f"❌ [SCHEDULER] Failed to insert notification for {box_email}")
                        
                except Exception as e:
                    print(f"❌ [SCHEDULER] Error inserting notification: {e}")

                send_calendar_service_not_found_notification(
                    sender_email=sender_email,
                    box_email=box_email,
                    subject=subject,
                    body=email_body,
                    summary_attachment=summary_attachments,
                    timestamp=notification_timestamp
                )
                return
            
            # CASE - EVENT DELETION FAILED ✅
            if status == "EVENT_DELETION_FAILED":
                print(f"ℹ️ [WORKFLOW] Event deletion failed - sending notification.")

                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "human_response": True,
                    "status": ThreadStatus.HUMAN_REVIEW.value
                }

                try:
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error updating thread: {e}")

                try:
                    notification_success = insert_notification_sync(
                        email=box_email,
                        notification_type="EVENT_DELETION_FAILED",
                        email_id=email_id,
                        text=None
                    )
                    
                    if not notification_success:
                        print(f"❌ [SCHEDULER] Failed to insert notification for {box_email}")
                        
                except Exception as e:
                    print(f"❌ [SCHEDULER] Error inserting notification: {e}")

                send_event_deletion_failed_notification(
                    sender_email=sender_email,
                    box_email=box_email,
                    subject=subject,
                    body=email_body,
                    summary_attachment=summary_attachments,
                    timestamp=notification_timestamp
                )
                return
            
            # CASE - LOW CONFIDENCE WRITER ✅
            if status == "LOW_CONFIDENCE_WRITER":
                print(f"⚠️ [WORKFLOW] LOW CONFIDENCE WRITER DETECTED!")
                
                service_id = None
                try:
                    service_id = get_subscription_service_id_by_email(box_email)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error getting service_id: {e}")

                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "human_response": True,
                    "status": ThreadStatus.HUMAN_REVIEW.value
                }

                # Create draft in provider if response_body is available
                draft_created = False
                draft_id = None
                if response_body and response_body.strip():
                    draft_created, draft_id = _create_draft_in_provider(
                        box_email=box_email,
                        sender_email=sender_email,
                        subject=subject,
                        response_body=response_body,
                        email_id=email_id,
                        reply_to_id=reply_to_id,
                        original_thread_id=original_thread_id,
                        microsoft_message_id=microsoft_message_id,
                        scheduled_event_details=scheduled_event_details
                    )
                    
                    # Save AI generated email record
                    ai_email_data = {
                        "thread_id": thread_id,
                        "message_id": draft_id,
                        "response_at_id": message_id,
                        "processed_at": now_tz,
                        "duration": 0, #TODO calculate duration
                        "priority_score": priority_score,
                        "body": response_body,
                        "service_id": service_id,
                        "outcome": EmailOutcome.DRAFT.value
                    }
                    
                    try:
                        save_ai_generated_email(ai_email_data)
                    except Exception as e:
                        print(f"❌ [WORKFLOW] Error saving draft: {e}")
                else:
                    print(f"⚠️ [LOW_CONFIDENCE_WRITER] No response body available - skipping draft creation")

                try:
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error updating thread: {e}")

                try:
                    notification_success = insert_notification_sync(
                        email=box_email,
                        notification_type="LOW_CONFIDENCE_WRITER",
                        email_id=email_id,
                        text=None
                    )
                    
                    if not notification_success:
                        print(f"❌ [SCHEDULER] Failed to insert notification for {box_email}")
                        
                except Exception as e:
                    print(f"❌ [SCHEDULER] Error inserting notification: {e}")

                send_low_confidence_writer_notification(
                    sender_email=sender_email,
                    box_email=box_email,
                    subject=subject,
                    body=email_body,
                    summary_attachment=summary_attachments,
                    timestamp=notification_timestamp
                )
                return
            

            # CASE - generic human review ✅  TODO gestire i vari casi (dopo la mail, request_document e altro)
            thread_data = {
                "category": category,
                "subcategory": subcategory,
                "summary": summary,
                "extended_summary": extended_summary,
                "human_response": True,
                "status": ThreadStatus.HUMAN_REVIEW.value
            }

            try:
                update_thread(thread_id, thread_data)
            except Exception as e:
                print(f"❌ [WORKFLOW] Error updating thread: {e}")

            try:
                notification_success = insert_notification_sync(
                    email=box_email,
                    notification_type="HUMAN_REVIEW",
                    email_id=email_id,
                    text=None
                )
                
                if not notification_success:
                    print(f"❌ [SCHEDULER] Failed to insert notification for {box_email}")
                    
            except Exception as e:
                print(f"❌ [SCHEDULER] Error inserting notification: {e}")

            return

        else:
            # CASE - email ready to send ✅
            if status == "EMAIL_READY_TO_SEND":

                service_id = None
                try:
                    service_id = get_subscription_service_id_by_email(box_email)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error getting service_id: {e}")

                new_message_id = None

                # TODO filtro temporaneo
                if box_email in ["dev1@example.com", "dev4@example.com", "customer@example.com"]:
                    print(f"[WORKFLOW] Skipping email sending for {box_email}")
                    return
                # ----------------------------------------

                # Check if draft mode is enabled
                user_config = workflow_result.get("user_config", {})
                draft_mode = user_config.get("draft", False)
                
                if draft_mode:
                    print(f"📝 [WORKFLOW] Draft mode enabled - Creating draft instead of sending...")
                else:
                    print(f"📧 [WORKFLOW] Sending email...")

                try:

                    # Get email service data
                    email_service_data = get_email_service_data(box_email)
                    if not email_service_data:
                        raise Exception(f"No email service data found for {box_email}")

                    provider = email_service_data.get("email_provider")
                    if not provider:
                        raise Exception(f"No email provider configured for {box_email}")

                    # Add AI disclaimer to the response body
                    response_body_with_disclaimer = _wrap_body_with_disclaimer(response_body)

                    # Prepare payload
                    payload = {
                        "email": sender_email,
                        "subject": subject,
                        "body": response_body_with_disclaimer,
                    }

                    # Generate ICS attachment if event was scheduled/rescheduled
                    if scheduled_event_details:
                        ics_attachment = _create_ics_attachment(scheduled_event_details)
                        if ics_attachment:
                            payload["attachments"] = [ics_attachment]
                            print(f"📎 [WORKFLOW] ICS attachment generated for event code: {scheduled_event_details.get('event_code')}")

                    senders_url = os.getenv("SENDERS_URL")
                    endpoint = ""

                    if provider == "google":
                        if draft_mode:
                            endpoint = f"{senders_url}/send-email/draft-gmail"
                        else:
                            endpoint = f"{senders_url}/send-email/send-gmail"
                        payload["hashed_access_token"] = email_service_data.get("hashed_access_token")
                        payload["original_thread_id"] = original_thread_id
                        payload["message_id"] = message_id
                    elif provider == "microsoft":
                        if draft_mode:
                            endpoint = f"{senders_url}/send-email/draft-microsoft"
                        else:
                            endpoint = f"{senders_url}/send-email/send-microsoft"
                        payload["hashed_access_token"] = email_service_data.get("hashed_access_token")
                        # Use microsoft_message_id (internal Graph ID) for replies, not the RFC message_id
                        payload["message_id"] = microsoft_message_id
                    elif provider == "imap":
                        print("[DEBUG-AUTOMATION] imap")
                        print("[DEBUG-AUTOMATION] email_service_data: ", email_service_data)
                        if draft_mode:
                            endpoint = f"{senders_url}/send-email/draft-imap"
                            # Get IMAP config from database, fallback to SMTP server conversion if not configured
                            imap_server = email_service_data.get("imap_server")
                            if not imap_server:
                                # Fallback: convert SMTP server to IMAP server
                                smtp_server = email_service_data.get("smtp_server", "")
                                imap_server = smtp_server.replace("smtp.", "imap.") if smtp_server.startswith("smtp.") else smtp_server
                            imap_port = email_service_data.get("imap_port") or 993
                            payload["imap_server"] = imap_server
                            payload["imap_port"] = imap_port
                            payload["imap_email"] = box_email
                            payload["password"] = email_service_data.get("hashed_password")
                            payload["reply_to_id"] = reply_to_id
                            payload["message_id"] = message_id
                        else:
                            endpoint = f"{senders_url}/send-email/send-smtp"
                            payload["smtp_server"] = email_service_data.get("smtp_server")
                            payload["smtp_port"] = email_service_data.get("smtp_port")
                            payload["smtp_email"] = box_email
                            payload["password"] = email_service_data.get("hashed_password")
                            payload["reply_to_id"] = reply_to_id
                            payload["message_id"] = message_id
                    else:
                        raise Exception(f"Unknown email provider: {provider}")

                    # Send request
                    response = requests.post(endpoint, json=payload)
                    response.raise_for_status()
                    
                    result = response.json()
                    new_message_id = result.get("message_id") or result.get("draft_id")
                    
                    if not result.get("success"):
                        raise Exception(f"Email {'draft creation' if draft_mode else 'sending'} failed: {result.get('message')}")

                    if draft_mode:
                        print(f"✅ [WORKFLOW] Draft created successfully via {provider}")
                    else:
                        print(f"✅ [WORKFLOW] Email sent successfully via {provider}")
                    
                    """
                    # Update ai_generated_email outcome to SENT
                    try:
                        update_ai_generated_email_outcome(thread_id, EmailOutcome.SENT.value)
                    except Exception as update_error:
                        print(f"❌ [WORKFLOW] Error updating ai_generated_email outcome: {update_error}")
                    """
                    
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error sending email: {e}")
                    
                    try:
                        # Send EMAIL_NOT_SENT notification
                        send_email_not_sent_notification(
                            sender_email=sender_email,
                            box_email=box_email,
                            subject=subject,
                            body=email_body,
                            summary_attachment=summary_attachments,
                            timestamp=notification_timestamp
                        )
                    except Exception as notif_error:
                        print(f"❌ [WORKFLOW] Error sending EMAIL_NOT_SENT notification: {notif_error}")
                    
                    # Save notification in database
                    try:
                        insert_notification_sync(
                            email=box_email,
                            notification_type="EMAIL_NOT_SENT",
                            email_id=email_id,
                            text=None
                        )
                    except Exception as notif_error:
                        print(f"❌ [WORKFLOW] Error inserting notification: {notif_error}")
                    
                    # Save ai_generated_email with outcome FAILED_TO_SEND
                    try:
                        ai_email_data = {
                            "thread_id": thread_id,
                            "message_id": None,
                            "response_at_id": message_id,
                            "processed_at": now_tz,
                            "duration": 0, #TODO calculate duration
                            "priority_score": priority_score,
                            "body": response_body,
                            "service_id": service_id,
                            "outcome": EmailOutcome.FAILED_TO_SEND.value
                        }

                        save_ai_generated_email(ai_email_data)
                    except Exception as save_error:
                        print(f"❌ [WORKFLOW] Error saving ai_generated_email: {save_error}")
                    
                    # Update thread with processed_at and status=PROCESSED
                    try:
                        thread_data = {
                            "category": category,
                            "subcategory": subcategory,
                            "summary": summary,
                            "extended_summary": extended_summary,
                            "status": ThreadStatus.HUMAN_REVIEW.value,
                        }
                        update_thread(thread_id, thread_data)
                    except Exception as update_error:
                        print(f"❌ [WORKFLOW] Error updating thread: {update_error}")

                    return
        
                # Save ai_generated_email in database and update thread
                ai_email_data = {
                    "thread_id": thread_id,
                    "message_id": new_message_id,
                    "response_at_id": message_id,
                    "processed_at": now_tz,
                    "duration": 0, #TODO calculate duration
                    "priority_score": priority_score,
                    "body": response_body,
                    "service_id": service_id,
                    "outcome": EmailOutcome.DRAFT.value if draft_mode else EmailOutcome.SENT.value
                }

                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "status": ThreadStatus.HUMAN_REVIEW.value if draft_mode else ThreadStatus.PROCESSED.value,
                }
                
                # Only add these fields when actually sending (not draft mode)
                if not draft_mode:
                    thread_data["last_message_id"] = new_message_id
                    thread_data["last_message_at"] = now_tz
                    thread_data["last_sender_email"] = box_email

                try:
                    if not draft_mode:
                        # Save the email first to get the email_id
                        saved_email_id = save_ai_generated_email(ai_email_data)
                        # Update history with both message_id and email_id
                        insert_new_mail_in_history_thread(thread_id, new_message_id, saved_email_id)
                    else:
                        save_ai_generated_email(ai_email_data)
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error saving AI generated email: {e}")

                return

            # CASE - generic automation completed ✅
            thread_data = {
                "category": category,
                "subcategory": subcategory,
                "summary": summary,
                "extended_summary": extended_summary,
                "status": ThreadStatus.PROCESSED.value
            }

            try:
                update_thread(thread_id, thread_data)
            except Exception as e:
                print(f"❌ [WORKFLOW] Error updating thread: {e}")

            return
                
        
        return
    
    return


