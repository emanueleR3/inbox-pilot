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
        """
        Main processing method for incoming email messages.
        
        Flow:
        1. Advanced filtering and thread creation
        2. Determine AI processing need
        3. Route to appropriate workflow
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            Processing result or None if message was filtered out
        """
        try:
            print(f"🚀 [PROCESSOR] Processing message: {email_data.get('message_id')} from {email_data.get('from')}")
            
            # Step 1: Clean email content before processing
            email_data = self.email_cleaner.clean_email_content(email_data)
            
            # Step 2: Apply advanced filtering
            filter_result = await self.filter.process_message(email_data)
            
            if not filter_result:
                print(f"🚫 [PROCESSOR] Message filtered out")
                return None
            
            # Step 3: Handle the result based on filter outcome
            action = filter_result.get("action")
            email_data["action"] = action
            
            if action == "send_to_summarizer":
                # TODO summarizer
                return {}

            if action == "thread_created":
                # New thread was created
                thread_data = filter_result.get("thread", {})
                needs_ai = filter_result.get("needs_ai", False)
                thread_id = thread_data.get("thread_id")
                
                # Process attachments for the new thread
                if thread_id and email_data.get("attachments"):
                    print(f"📎 [PROCESSOR] Processing attachments for new thread {thread_id}")
                    try:
                        processed_attachments = await self.attachment_service.process_attachments(
                            email_data, thread_id
                        )
                        thread_data["attachments_processed"] = len(processed_attachments)
                    except Exception as e:
                        print(f"❌ [PROCESSOR] Attachment processing failed: {e}")
                        thread_data["attachments_processed"] = 0
                
                if needs_ai:
                    print(f"🤖 [PROCESSOR] Thread created from external user - sending to AI workflow")
                    print(f"🧵 Thread ID: {thread_data.get('thread_id')}")
                    print(f"📧 Subject: {thread_data.get('subject')}")
                    print(f"👤 Sender: {thread_data.get('sender_email')}")
                    print(f"📮 Mailbox: {thread_data.get('box_email')}")
                    
                    # Prepare and send automation payload
                    automation_payload = self._prepare_automation_payload(
                        email_data, thread_data, processed_attachments if 'processed_attachments' in locals() else []
                    )
                    await self.send_to_automation(automation_payload)
                else:
                    print(f"👤 [PROCESSOR] Thread created from user - no AI processing needed")
                
                return {
                    "status": "thread_created",
                    "thread_id": thread_data.get("thread_id"),
                    "needs_ai_processing": needs_ai,
                    "attachments_processed": thread_data.get("attachments_processed", 0)
                }
            
            elif action == "process":
                # Message needs further processing
                print(f"📋 [PROCESSOR] Message ready for AI processing")
                # TODO: Implement AI workflow routing
                return {
                    "status": "ready_for_ai",
                    "needs_ai_processing": filter_result.get("needs_ai", True)
                }
            
            elif action == "thread_updated":
                # Existing thread was updated with new message
                thread_id = filter_result.get("thread_id")
                
                # Process attachments for the updated thread
                if thread_id and email_data.get("attachments"):
                    print(f"📎 [PROCESSOR] Processing attachments for updated thread {thread_id}")
                    try:
                        processed_attachments = await self.attachment_service.process_attachments(
                            email_data, thread_id
                        )
                        attachments_count = len(processed_attachments)
                    except Exception as e:
                        print(f"❌ [PROCESSOR] Attachment processing failed: {e}")
                        attachments_count = 0
                else:
                    attachments_count = 0
                
                print(f"📝 [PROCESSOR] Thread {thread_id} updated with reply - sending to AI workflow")
                
                # Prepare and send automation payload for thread update
                automation_payload = self._prepare_automation_payload(
                    email_data, {"thread_id": thread_id, "box_email": email_data.get("user_email")}, 
                    processed_attachments if 'processed_attachments' in locals() else []
                )
                await self.send_to_automation(automation_payload)
                
                return {
                    "status": "thread_updated",
                    "thread_id": thread_id,
                    "needs_ai_processing": True,
                    "attachments_processed": attachments_count
                }
            
            elif action == "human_response_marked":
                # Human response was marked for thread
                thread_id = filter_result.get("thread_id")
                print(f"👤 [PROCESSOR] Human response marked for thread {thread_id}")
                # TODO: Send notification, update summary and category
                return {
                    "status": "human_response_needed",
                    "thread_id": thread_id,
                    "needs_ai_processing": False
                }
            
            elif action == "skip":
                # Message should be skipped (duplicate)
                reason = filter_result.get("reason", "unknown")
                print(f"🚫 [PROCESSOR] Message skipped: {reason}")
                return {
                    "status": "skipped",
                    "reason": reason,
                    "needs_ai_processing": False
                }
            
            else:
                print(f"❓ [PROCESSOR] Unknown filter result action: {action}")
                return None
                
        except Exception as e:
            print(f"❌ [PROCESSOR] Error processing message: {e}")
            return None
    
    async def send_to_automation(self, automation_payload: dict) -> bool:
        """
        Send automation payload to automations module via HTTP.
        
        Args:
            automation_payload: Complete automation payload dictionary
            
        Returns:
            #TODO
        """
        try:
            print(f"📤 [PROCESSOR] Sending to automation API: {self.automation_api_url}")
            print(f"🧵 Thread ID: {automation_payload.get('thread_id')}")
            print(f"📦 [PAYLOAD] {automation_payload}")  # Log del payload completo
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.automation_api_url,
                    json=automation_payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ [PROCESSOR] Successfully sent to automation API")
                        print(f"📋 Response: {result.get('status')} - {result.get('message')}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ [PROCESSOR] Automation API error ({response.status}): {error_text}")
                        return False
                
        except aiohttp.ClientError as e:
            print(f"❌ [PROCESSOR] HTTP request failed: {e}")
            return False
        except Exception as e:
            print(f"❌ [PROCESSOR] Unexpected error sending to automation: {e}")
            return False
    
    def _prepare_automation_payload(self, email_data: dict, thread_data: dict, processed_attachments: list) -> dict:
        """
        Prepare payload for automation service with all thread information.
        
        Args:
            email_data: Original email data
            thread_data: Thread information (must contain thread_id)
            processed_attachments: List of processed attachments with IDs
            
        Returns:
            Complete automation payload dictionary
        """
        # Extract attachment IDs from processed attachments
        attachment_ids = []
        for attachment in processed_attachments:
            if attachment.get("attachment_id"):
                attachment_ids.append(attachment["attachment_id"])
        
        # Get full thread data from database to retrieve category, subcategory, extended_summary
        thread_id = thread_data.get("thread_id")
        full_thread_data = None
        
        if thread_id:
            try:
                full_thread_data = self.thread_repo.get_thread_by_id(thread_id)
            except Exception as e:
                print(f"⚠️ [PROCESSOR] Failed to retrieve full thread data: {e}")
        
        # Extract thread fields with fallbacks
        category = None
        subcategory = None
        extended_summary = None
        has_attachments = len(attachment_ids) > 0
        
        if full_thread_data:
            category = full_thread_data.get("category")
            subcategory = full_thread_data.get("subcategory")
            extended_summary = full_thread_data.get("extended_summary")
            has_attachments = full_thread_data.get("has_attachments", has_attachments)
        
        # Build complete automation payload
        automation_payload = {
            "thread_id": thread_id,
            "message_id": email_data.get("message_id"),
            "reply_to_id": email_data.get("reply_to_id", "no"),
            "box_email": thread_data.get("box_email") or email_data.get("user_email"),
            "from": email_data.get("from"),
            "to": email_data.get("to"),
            "cc": email_data.get("cc"),
            "subject": email_data.get("subject"),
            "subcategory": subcategory,
            "category": category,
            "body": email_data.get("body_text", email_data.get("body", "")),  # Use cleaned body first, fallback to original
            "provider": email_data.get("provider"),
            "attachment_ids": attachment_ids,
            "has_attachments": has_attachments,
            "extended_summary": extended_summary,
            "no_reply": email_data.get("no_reply", False),
            "action": email_data.get("action"),
            "summarizer_only": email_data.get("summarizer_only", False)
        }
        
        return automation_payload