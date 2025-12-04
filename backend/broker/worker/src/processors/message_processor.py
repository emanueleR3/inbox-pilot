"""
Main email processor that orchestrates filtering, thread management, and AI workflow routing.
This is the central processing hub for all email messages.
"""

from src.filters.advanced_filter import AdvancedEmailFilter
from src.managers.thread_manager import ThreadManager
from src.utils.attachment_service import AttachmentService
from src.utils.email_cleaner import EmailCleaner
from src.repositories.thread_repository import ThreadRepository
from typing import Optional
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

def log(msg):
    print(msg)

class EmailProcessor:
    """
    Central email processor that coordinates all email processing operations.
    Handles filtering, thread management, database operations, and AI workflow routing.
    """
    
    def __init__(self):
        self.filter = AdvancedEmailFilter()
        self.thread_manager = ThreadManager()
        self.attachment_service = AttachmentService()
        self.email_cleaner = EmailCleaner()
        self.thread_repo = ThreadRepository()
        # Automation API endpoint configuration
        self.automation_api_url = os.getenv("AUTOMATION_API_URL", "http://automations:8010/") + "workflows/process-email"
    
    async def process_message(self, email_data: dict) -> Optional[dict]:
        try:
            log(f"[PROCESSOR] Processing message {email_data.get('message_id')} from {email_data.get('from')}")
            
            # Step 1: Clean email content before processing
            email_data = self.email_cleaner.clean_email_content(email_data)
            
            # Step 2: Apply advanced filtering
            filter_result = await self.filter.process_message(email_data)
            
            if not filter_result:
                log(f"[PROCESSOR] Message filtered out")
                return None
            
            # Step 3: Handle the result based on filter outcome
            action = filter_result.get("action")
            summarizer_only = filter_result.get("summarizer_only", False)
            email_data["action"] = action
            email_data["summarizer_only"] = summarizer_only
            
            log(f"[PROCESSOR] Action decided: {action}")
            
            if action == "send_to_summarizer":
                needs_ai = filter_result.get("needs_ai", False)
                reply_to_id = email_data.get("reply_to_id")
                box_email = email_data.get("user_email")
                thread_id = None
                
                if reply_to_id and reply_to_id.lower() != "no":
                    thread = self.thread_repo.find_thread_by_reply_to(reply_to_id, box_email)
                    if thread:
                        thread_id = thread.get("thread_id")
                        log(f"[PROCESSOR] Found thread {thread_id} for summarizer")
                    else:
                        log(f"[PROCESSOR] No thread found for reply_to_id: {reply_to_id}")
                
                if not thread_id:
                    log(f"[PROCESSOR] Cannot send to summarizer without thread_id")
                    return {
                        "status": "skipped",
                        "reason": "no_thread_found_for_summarizer",
                        "needs_ai_processing": False
                    }
                
                try:
                    processed_attachments = []
                    if thread_id and email_data.get("attachments"):
                        log(f"[PROCESSOR] Processing attachments for summarizer in thread {thread_id}")
                        try:
                            processed_attachments = await self.attachment_service.process_attachments(
                                email_data, thread_id
                            )
                        except Exception as e:
                            log(f"[PROCESSOR] Attachment processing failed: {e}")
                    
                    automation_payload = self._prepare_automation_payload(
                        email_data, {"thread_id": thread_id, "box_email": box_email}, 
                        processed_attachments
                    )

                    await self.send_to_automation(automation_payload)
                except Exception as e:
                    log(f"[PROCESSOR] Failed to send to summarizer: {e}")

                return {
                    "status": "sent_to_summarizer",
                    "thread_id": thread_id,
                    "needs_ai_processing": False,
                }


            if action == "thread_created":
                thread_data = filter_result.get("thread", {})
                needs_ai = filter_result.get("needs_ai", False)
                thread_id = thread_data.get("thread_id")
                
                processed_attachments = []
                if thread_id and email_data.get("attachments"):
                    log(f"[PROCESSOR] Processing attachments for new thread {thread_id}")
                    try:
                        processed_attachments = await self.attachment_service.process_attachments(
                            email_data, thread_id
                        )
                        thread_data["attachments_processed"] = len(processed_attachments)
                    except Exception as e:
                        log(f"[PROCESSOR] Attachment processing failed: {e}")
                        thread_data["attachments_processed"] = 0
                
                if needs_ai:
                    log(f"[PROCESSOR] Thread created from external user - sending to AI workflow")
                    log(f"[PROCESSOR] Thread ID: {thread_data.get('thread_id')}")
                    
                    automation_payload = self._prepare_automation_payload(
                        email_data, thread_data, processed_attachments
                    )
                    await self.send_to_automation(automation_payload)
                else:
                    log(f"[PROCESSOR] Thread created from user - no AI processing needed")
                
                return {
                    "status": "thread_created",
                    "thread_id": thread_data.get("thread_id"),
                    "needs_ai_processing": needs_ai,
                    "attachments_processed": thread_data.get("attachments_processed", 0)
                }
            
            elif action == "process":
                log(f"[PROCESSOR] Message ready for AI processing")
                return {
                    "status": "ready_for_ai",
                    "needs_ai_processing": filter_result.get("needs_ai", True)
                }
            
            elif action == "thread_updated":
                thread_id = filter_result.get("thread_id")
                
                processed_attachments = []
                attachments_count = 0
                if thread_id and email_data.get("attachments"):
                    log(f"[PROCESSOR] Processing attachments for updated thread {thread_id}")
                    try:
                        processed_attachments = await self.attachment_service.process_attachments(
                            email_data, thread_id
                        )
                        attachments_count = len(processed_attachments)
                    except Exception as e:
                        log(f"[PROCESSOR] Attachment processing failed: {e}")
                        attachments_count = 0
                
                log(f"[PROCESSOR] Thread {thread_id} updated with reply - sending to AI workflow")
                
                automation_payload = self._prepare_automation_payload(
                    email_data, {"thread_id": thread_id, "box_email": email_data.get("user_email")}, 
                    processed_attachments
                )
                await self.send_to_automation(automation_payload)
                
                return {
                    "status": "thread_updated",
                    "thread_id": thread_id,
                    "needs_ai_processing": True,
                    "attachments_processed": attachments_count
                }
            
            elif action == "human_response_marked":
                thread_id = filter_result.get("thread_id")
                log(f"[PROCESSOR] Human response marked for thread {thread_id}")
                return {
                    "status": "human_response_needed",
                    "thread_id": thread_id,
                    "needs_ai_processing": False
                }
            
            elif action == "skip":
                reason = filter_result.get("reason", "unknown")
                log(f"[PROCESSOR] Message skipped: {reason}")
                return {
                    "status": "skipped",
                    "reason": reason,
                    "needs_ai_processing": False
                }
            
            else:
                log(f"[PROCESSOR] Unknown filter result action: {action}")
                return None
                
        except Exception as e:
            log(f"[PROCESSOR] Error processing message: {e}")
            return None
    
    async def send_to_automation(self, automation_payload: dict) -> bool:
        log("[PROCESSOR] Sending to automation API...")
        log(f"URL: {self.automation_api_url}")
        log(f"Thread: {automation_payload.get('thread_id')}")
        log(f"Payload: {automation_payload}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.automation_api_url,
                    json=automation_payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:

                    text = await response.text()

                    if response.status == 200:
                        log("[PROCESSOR] Automation API responded with 200 OK")
                        return True

                    log(f"[PROCESSOR] Automation API error {response.status}: {text}")
                    return False

        except aiohttp.ClientError as e:
            log(f"[PROCESSOR] ClientError sending to automation: {e}")
            return False

        except Exception as e:
            log(f"[PROCESSOR] Unexpected error sending to automation: {e}")
            return False
    
    def _prepare_automation_payload(self, email_data: dict, thread_data: dict, processed_attachments: list) -> dict:
        attachment_ids = []

        for att in processed_attachments:
            if att.get("attachment_id"):
                attachment_ids.append(att["attachment_id"])

        thread_id = thread_data.get("thread_id")

        try:
            full_thread = self.thread_repo.get_thread_by_id(thread_id)
        except:
            full_thread = None

        category = full_thread.get("category") if full_thread else None
        subcategory = full_thread.get("subcategory") if full_thread else None
        extended_summary = full_thread.get("extended_summary") if full_thread else None

        payload = {
            "thread_id": thread_id,
            "message_id": email_data.get("message_id"),
            "microsoft_message_id": email_data.get("microsoft_message_id"),
            "reply_to_id": email_data.get("reply_to_id", "no"),
            "box_email": thread_data.get("box_email") or email_data.get("user_email"),
            "from": email_data.get("from"),
            "to": email_data.get("to"),
            "cc": email_data.get("cc"),
            "subject": email_data.get("subject"),
            "body": email_data.get("body_text", email_data.get("body")),
            "provider": email_data.get("provider"),
            "subcategory": subcategory,
            "category": category,
            "extended_summary": extended_summary,
            "attachment_ids": attachment_ids,
            "has_attachments": len(attachment_ids) > 0,
            "no_reply": email_data.get("no_reply", False),
            "action": email_data.get("action"),
            "summarizer_only": email_data.get("summarizer_only", False),
            "original_thread_id": email_data.get("original_thread_id"),
        }

        log(f"[PROCESSOR] Automation payload prepared: {payload}")

        return payload
