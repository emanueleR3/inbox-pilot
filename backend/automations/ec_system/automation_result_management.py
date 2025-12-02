from db_client import (
    insert_notification_sync,
    save_ai_generated_email,
    get_subscription_service_id_by_email,
    update_thread,
    update_ai_generated_email_outcome,
    get_email_service_data,
    insert_new_mail_in_history_thread
)
import os
import requests
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
    send_low_confidence_writer_notification
)
from models import ThreadStatus, EmailOutcome
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

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
    sender_email = extracted_info.get("from", "unknown")
    subject = extracted_info.get("subject", "No subject")
    thread_id = extracted_info.get("thread_id", None)
    replay_to_id = extracted_info.get("reply_to_id", None)
    summary = workflow_result.get("mail_summary", "")
    extended_summary = workflow_result.get("extended_summary", None)
    cc_emails = extracted_info.get("cc", "")
    has_attachments = extracted_info.get("has_attachments", False)
    priority_score = workflow_result.get("priority_score", 0)
    response_body = workflow_result.get("written_email_body", "")
    category = workflow_result.get("category", "")
    subcategory = workflow_result.get("subcategory", "")
    email_body = extracted_info.get("email_body", "")
    summary_attachments = workflow_result.get("summary_attachments", None)
    now_tz = datetime.now(timezone.utc).isoformat()
    original_thread_id = workflow_result.get("original_thread_id", None)

    # ======= SUMMARIZER ONLY CHECK ======= ✅
    if workflow_result.get("summarizer_only", False):   
        print(f"⚠️ [WORKFLOW] Summarizer only. - Saving summary and extended summary")
        if not thread_id:
            print(f"❌ [WORKFLOW] No thread_id found in workflow result")
            return

        thread_data = {
            "summary": summary,
            "extended_summary": extended_summary,
            "cc_emails": cc_emails,
            "has_attachments": has_attachments
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
                message_id=message_id,
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
            body=workflow_result.get("email_body", ""),
            summary_attachment=workflow_result.get("summary_attachments")
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

            if workflow_result.get("needs_response", True):
                ai_email_data = { 
                    "thread_id": thread_id,
                    "response_at_id": message_id,
                    "processed_at": now_tz,
                    "duration": 0, #TODO calculate duration
                    "priority_score": priority_score,
                    "body": response_body,
                    "service_id": service_id,
                    "outcome": EmailOutcome.DRAFT.value
                }
                save_ai_generated_email(ai_email_data)

        except Exception as e:
            print(f"❌ [WORKFLOW] Error saving AI generated email: {e}")

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
        try:
            send_high_priority_notification(
                sender_email=sender_email,
                box_email=box_email,
                subject=subject,
                body=email_body,
                summary_attachment=summary_attachments
            )
        except Exception as e:
            print(f"❌ [PRIORITY_CONTROLLER] Error sending high priority notification: {e}")
        
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
                        message_id=message_id,
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
                    summary_attachment=summary_attachments
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
                    message_id=message_id,
                    text=f"Error extracting company information: {str(e)}"
                )

                send_information_not_present_notification(
                    sender_email=sender_email,
                    box_email=box_email,
                    subject=subject,
                    body=email_body,
                    summary_attachment=summary_attachments
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
                        message_id=message_id,
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
                    summary_attachment=summary_attachments
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
                        message_id=message_id,
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
                    summary_attachment=summary_attachments
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
                        message_id=message_id,
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
                        summary_attachment=summary_attachments
                    )
                else:
                    send_appointment_not_rescheduled_notification(
                        sender_email=sender_email,
                        box_email=box_email,
                        subject=subject,
                        body=email_body,
                        summary_attachment=summary_attachments
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
                        message_id=message_id,
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
                    summary_attachment=summary_attachments
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
                        message_id=message_id,
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
                    summary_attachment=summary_attachments
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
                        message_id=message_id,
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
                    summary_attachment=summary_attachments
                )
                return
            
            # CASE - LOW CONFIDENCE WRITER ✅
            if status == "LOW_CONFIDENCE_WRITER":
                print(f"⚠️ [WORKFLOW] LOW CONFIDENCE WRITER DETECTED!")
                
                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "human_response": True,
                    "status": ThreadStatus.HUMAN_REVIEW.value
                }

                ai_email_data = {
                    "thread_id": thread_id,
                    "response_at_id": message_id,
                    "processed_at": now_tz,
                    "duration": 0, #TODO calculate duration
                    "priority_score": priority_score,
                    "body": response_body,
                    "service_id": service_id,
                    "outcome": EmailOutcome.DRAFT.value
                }

                # Save draft in ai_generated_emails
                try:
                    save_ai_generated_email(ai_email_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error saving draft: {e}")

                try:
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error updating thread: {e}")

                try:
                    notification_success = insert_notification_sync(
                        email=box_email,
                        notification_type="LOW_CONFIDENCE_WRITER",
                        message_id=message_id,
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
                    summary_attachment=summary_attachments
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
                    message_id=message_id,
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

                try:
                    print(f"📧 [WORKFLOW] Sending email...")

                    # Get email service data
                    email_service_data = get_email_service_data(box_email)
                    if not email_service_data:
                        raise Exception(f"No email service data found for {box_email}")

                    provider = email_service_data.get("email_provider")
                    if not provider:
                        raise Exception(f"No email provider configured for {box_email}")

                    # Prepare payload TODO voglio rispondere all'email e non creare un nuovo thread
                    payload = {
                        "email": sender_email,
                        "subject": subject,
                        "body": response_body,
                    }

                    senders_url = os.getenv("SENDERS_URL")
                    endpoint = ""

                    if provider == "google":
                        endpoint = f"{senders_url}/send-email/send-gmail"
                        payload["hashed_access_token"] = email_service_data.get("hashed_access_token")
                        payload["original_thread_id"] = original_thread_id
                        payload["message_id"] = message_id
                    elif provider == "microsoft":
                        endpoint = f"{senders_url}/send-email/send-microsoft"
                        payload["hashed_access_token"] = email_service_data.get("hashed_access_token")
                        payload["message_id"] = message_id
                    elif provider == "imap":
                        endpoint = f"{senders_url}/send-email/send-smtp"
                        payload["smtp_server"] = email_service_data.get("smtp_server")
                        payload["smtp_port"] = email_service_data.get("smtp_port")
                        payload["smtp_email"] = box_email
                        payload["hashed_password"] = email_service_data.get("hashed_password")
                        payload["reply_to_id"] = replay_to_id
                        payload["message_id"] = message_id
                    else:
                        raise Exception(f"Unknown email provider: {provider}")

                    # Send request
                    response = requests.post(endpoint, json=payload)
                    response.raise_for_status()
                    
                    result = response.json()
                    new_message_id = result.get("message_id") # TODO da inserire
                    
                    if not result.get("success"):
                        raise Exception(f"Email sending failed: {result.get('message')}")

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
                            summary_attachment=summary_attachments
                        )
                    except Exception as notif_error:
                        print(f"❌ [WORKFLOW] Error sending EMAIL_NOT_SENT notification: {notif_error}")
                    
                    # Save notification in database
                    try:
                        insert_notification_sync(
                            email=box_email,
                            notification_type="EMAIL_NOT_SENT",
                            message_id=message_id,
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
                    "outcome": EmailOutcome.SENT.value
                }

                thread_data = {
                    "category": category,
                    "subcategory": subcategory,
                    "summary": summary,
                    "extended_summary": extended_summary,
                    "status": ThreadStatus.PROCESSED.value,
                    "last_message_id": new_message_id,
                    "last_message_at": now_tz,
                    "last_sender_email": box_email
                }

                try:
                    insert_new_mail_in_history_thread(thread_id, new_message_id)
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


