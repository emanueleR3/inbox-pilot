from db_client import (
    insert_notification_sync,
    save_ai_generated_email,
    get_subscription_service_id_by_email,
    update_thread,
    update_ai_generated_email_outcome
)
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
    send_email_not_sent_notification
)
from models import ThreadStatus, EmailOutcome
from datetime import datetime, timezone

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
    
    # ======= DANGEROUS EMAIL CHECK ======= ✅
    if workflow_result.get("dangerous_email", False):
        print(f"🚨 [WORKFLOW] DANGEROUS EMAIL DETECTED!")
        # Extract thread and message IDs from state
        extracted_info = workflow_result.get("extracted_info", {})
        message_id = extracted_info.get("message_id", "unknown")
        box_email = extracted_info.get("box_email", "unknown")

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
        extracted_info = workflow_result.get("extracted_info", {})
        message_id = extracted_info.get("message_id", "unknown")
        box_email = extracted_info.get("box_email", "unknown")
        thread_id = extracted_info.get("thread_id", "unknown")
        
        thread_data = {
            "category": workflow_result.get("category", ""),
            "summary": workflow_result.get("mail_summary", ""),
            "extended_summary": workflow_result.get("extended_summary", ""),
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
    if status == "END_HIGH_PRIORITY":
        print(f"🔥 [WORKFLOW] HIGH PRIORITY EMAIL DETECTED!")

        # Get extracted info for notifications
        extracted_info = workflow_result.get("extracted_info", {})
        message_id = extracted_info.get("message_id", "unknown")
        box_email = extracted_info.get("box_email", "unknown")
        thread_id = extracted_info.get("thread_id", "unknown")
        now_tz = datetime.now(timezone.utc)
        
        service_id = None
        try:
            service_id = get_subscription_service_id_by_email(box_email)
        except Exception as e:
            print(f"❌ [WORKFLOW] Error getting service_id: {e}")

        ai_email_data = {
            "thread_id": thread_id,
            "response_at_id": message_id,
            "processed_at": now_tz,
            "duration": 0, #TODO calculate duration
            "priority_score": workflow_result.get("priority_score", 0),
            "body": workflow_result.get("written_email_body", ""),
            "service_id": service_id,
            "outcome": EmailOutcome.DRAFT.value
        }

        thread_data = {
            "category": workflow_result.get("category", ""),
            "summary": workflow_result.get("mail_summary", ""),
            "extended_summary": workflow_result.get("extended_summary", ""),
            "human_response": True,
            "status": ThreadStatus.HIGH_PRIORITY.value
        }

        try:
            save_ai_generated_email(ai_email_data)
            update_thread(thread_id, thread_data)
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
                sender_email=extracted_info.get("from", "unknown"),
                box_email=box_email,
                subject=extracted_info.get("subject", "No subject"),
                body=workflow_result.get("email_body", ""),
                summary_attachment=workflow_result.get("summary_attachments")
            )
        except Exception as e:
            print(f"❌ [PRIORITY_CONTROLLER] Error sending high priority notification: {e}")
        
        return
    
    # ======= AUTOMATION EXECUTED CHECK =======
    if workflow_result.get("automation_executed", False):
        print(f"✅ [WORKFLOW] AUTOMATION EXECUTED SUCCESSFULLY!")

        human_response = workflow_result.get("human_response", None)
        #DEBUG
        print(f"DEBUG")
        print(f"="*20)
        print(f"Human response: {human_response}")
        print(f"\n="*20)

        if human_response:
            extracted_info = workflow_result.get('extracted_info', {})
            box_email = extracted_info.get('box_email', 'unknown')
            message_id = extracted_info.get('message_id', 'unknown')
            sender_email = extracted_info.get("from", "unknown")
            subject = extracted_info.get("subject", "No subject")


            # CASE - EVENT_INVITE with category INFORMATION_PROVIDED/CALENDAR_EVENT ⚠️
            if status == "EVENT_INVITE_HUMAN_RESPONSE_REQUIRED":
                print(f"⚠️ [WORKFLOW] EVENT INVITE DETECTED - SENDING NOTIFICATION")

                thread_data = {
                    "category": workflow_result.get("category", ""),
                    "subcategory": workflow_result.get("subcategory", ""),
                    "summary": workflow_result.get("mail_summary", ""),
                    "extended_summary": workflow_result.get("extended_summary", ""),
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
                    body=workflow_result.get("email_body", ""),
                    summary_attachment=workflow_result.get("summary_attachments")
                )
                return
            
            # CASE - COMPANY_INFO_EXTRACTION_FAILED ✅
            if status == "COMPANY_INFO_EXTRACTION_FAILED":
                print(f"⚠️ [WORKFLOW] COMPANY INFO EXTRACTION FAILED - SENDING NOTIFICATION")

                thread_data = {
                    "category": workflow_result.get("category", ""),
                    "subcategory": workflow_result.get("subcategory", ""),
                    "summary": workflow_result.get("mail_summary", ""),
                    "extended_summary": workflow_result.get("extended_summary", ""),
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
                    body=workflow_result.get('email_body', ''),
                    summary_attachment=workflow_result.get('summary_attachments', '')
                )
                return
            
            # CASE - EVENT_FOLLOWUP with needs response ⚠️
            if status == "EVENT_FOLLOWUP_HUMAN_RESPONSE_REQUIRED":
                print(f"⚠️ [WORKFLOW] EVENT FOLLOW-UP DETECTED - SENDING NOTIFICATION")

                thread_data = {
                    "category": workflow_result.get("category", ""),
                    "subcategory": workflow_result.get("subcategory", ""),
                    "summary": workflow_result.get("mail_summary", ""),
                    "extended_summary": workflow_result.get("extended_summary", ""),
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
                    body=workflow_result.get("email_body", ""),
                    summary_attachment=workflow_result.get('summary_attachments', '')
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
                    "category": workflow_result.get("category", ""),
                    "subcategory": workflow_result.get("subcategory", ""),
                    "summary": workflow_result.get("mail_summary", ""),
                    "extended_summary": workflow_result.get("extended_summary", ""),
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
                    body=workflow_result.get("email_body", ""),
                    summary_attachment=workflow_result.get('summary_attachments')
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
                    "category": workflow_result.get("category", ""),
                    "subcategory": workflow_result.get("subcategory", ""),
                    "summary": workflow_result.get("mail_summary", ""),
                    "extended_summary": workflow_result.get("extended_summary", ""),
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
                        body=workflow_result.get("email_body", ""),
                        summary_attachment=workflow_result.get('summary_attachments')
                    )
                else:
                    send_appointment_not_rescheduled_notification(
                        sender_email=sender_email,
                        box_email=box_email,
                        subject=subject,
                        body=workflow_result.get("email_body", ""),
                        summary_attachment=workflow_result.get('summary_attachments')
                    )

                return
            
            # CASE - EVENT CODE NOT FOUND ✅
            if status == "EVENT_CODE_NOT_FOUND":
                print(f"ℹ️ [WORKFLOW] Event code not found in database - sending notification.")

                thread_data = {
                    "category": workflow_result.get("category", ""),
                    "subcategory": workflow_result.get("subcategory", ""),
                    "summary": workflow_result.get("mail_summary", ""),
                    "extended_summary": workflow_result.get("extended_summary", ""),
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
                    body=workflow_result.get("email_body", ""),
                    summary_attachment=workflow_result.get('summary_attachments')
                )
                return
            
            # CASE - CALENDAR SERVICE NOT FOUND ✅
            if status == "CALENDAR_SERVICE_NOT_FOUND":
                print(f"ℹ️ [WORKFLOW] Calendar service not found for user - sending notification.")

                thread_data = {
                    "category": workflow_result.get("category", ""),
                    "subcategory": workflow_result.get("subcategory", ""),
                    "summary": workflow_result.get("mail_summary", ""),
                    "extended_summary": workflow_result.get("extended_summary", ""),
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
                    body=workflow_result.get("email_body", ""),
                    summary_attachment=workflow_result.get('summary_attachments')
                )
                return
            
            # CASE - EVENT DELETION FAILED ✅
            if status == "EVENT_DELETION_FAILED":
                print(f"ℹ️ [WORKFLOW] Event deletion failed - sending notification.")

                thread_data = {
                    "category": workflow_result.get("category", ""),
                    "subcategory": workflow_result.get("subcategory", ""),
                    "summary": workflow_result.get("mail_summary", ""),
                    "extended_summary": workflow_result.get("extended_summary", ""),
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
                    body=workflow_result.get("email_body", ""),
                    summary_attachment=workflow_result.get('summary_attachments')
                )
                return
            
            # CASE - generic human review ✅  TODO gestire i vari casi (dopo la mail, request_document e altro)
            thread_data = {
                "category": workflow_result.get("category", ""),
                "subcategory": workflow_result.get("subcategory", ""),
                "summary": workflow_result.get("mail_summary", ""),
                "extended_summary": workflow_result.get("extended_summary", ""),
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
            subcategory = workflow_result.get("subcategory", "")

            # CASE - email ready to send ⚠️
            if status == "EMAIL_READY_TO_SEND":
                # Get extracted info for notifications
                extracted_info = workflow_result.get("extracted_info", {})
                message_id = extracted_info.get("message_id", "unknown")
                box_email = extracted_info.get("box_email", "unknown")
                thread_id = extracted_info.get("thread_id", "unknown")
                now_tz = datetime.now(timezone.utc)
        
                service_id = None
                try:
                    service_id = get_subscription_service_id_by_email(box_email)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error getting service_id: {e}")

                ai_email_data = {
                    "thread_id": thread_id,
                    "message_id": None, #TODO da inserire
                    "response_at_id": message_id,
                    "processed_at": now_tz,
                    "duration": 0, #TODO calculate duration
                    "priority_score": workflow_result.get("priority_score", 0),
                    "body": workflow_result.get("written_email_body", ""),
                    "service_id": service_id,
                    "outcome": EmailOutcome.READY_TO_SEND.value
                }

                thread_data = {
                    "category": workflow_result.get("category", ""),
                    "subcategory": workflow_result.get("subcategory", ""),
                    "summary": workflow_result.get("mail_summary", ""),
                    "extended_summary": workflow_result.get("extended_summary", ""),
                    "status": ThreadStatus.PROCESSED.value
                }

                try:
                    save_ai_generated_email(ai_email_data)
                    update_thread(thread_id, thread_data)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error saving AI generated email: {e}")

                try:
                    print(f"📧 [WORKFLOW] Sending email...")
                    # TODO send email (NON IMPLEMENTARE QUESTO)
                except Exception as e:
                    print(f"❌ [WORKFLOW] Error sending email: {e}")
                    
                    # Send EMAIL_NOT_SENT notification
                    send_email_not_sent_notification(
                        sender_email=extracted_info.get("from", "unknown"),
                        box_email=box_email,
                        subject=extracted_info.get("subject", "No subject"),
                        body=workflow_result.get("email_body", ""),
                        summary_attachment=workflow_result.get("summary_attachments")
                    )
                    
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
                    
                    # Update ai_generated_email outcome to FAILED_TO_SEND
                    try:
                        update_ai_generated_email_outcome(thread_id, EmailOutcome.FAILED_TO_SEND.value)
                    except Exception as update_error:
                        print(f"❌ [WORKFLOW] Error updating ai_generated_email outcome: {update_error}")
                    
                    # Update thread to human_response=True and status=HUMAN_REVIEW
                    thread_data_error = {
                        "human_response": True,
                        "status": ThreadStatus.HUMAN_REVIEW.value
                    }
                    try:
                        update_thread(thread_id, thread_data_error)
                    except Exception as thread_error:
                        print(f"❌ [WORKFLOW] Error updating thread: {thread_error}")

                return

            # CASE - generic automation completed ✅
            thread_data = {
                "category": workflow_result.get("category", ""),
                "subcategory": workflow_result.get("subcategory", ""),
                "summary": workflow_result.get("mail_summary", ""),
                "extended_summary": workflow_result.get("extended_summary", ""),
                "status": ThreadStatus.PROCESSED.value
            }

            try:
                update_thread(thread_id, thread_data)
            except Exception as e:
                print(f"❌ [WORKFLOW] Error updating thread: {e}")

            return
                
        
        return
    

    return


