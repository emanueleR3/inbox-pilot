"""
Improved EmailProcessor with structured, colored logging and better error reporting.
"""

from src.filters.advanced_filter import AdvancedEmailFilter
from src.managers.thread_manager import ThreadManager
from src.utils.attachment_service import AttachmentService
from src.utils.email_cleaner import EmailCleaner
from src.repositories.thread_repository import ThreadRepository

from typing import Optional
import aiohttp
import json
import os
import traceback
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------
# 🔵 Utility: colored, structured logger
# ---------------------------------------------------------
def log_info(msg):
    print(f"\033[96mℹ️  {msg}\033[0m")

def log_success(msg):
    print(f"\033[92m✅ {msg}\033[0m")

def log_warn(msg):
    print(f"\033[93m⚠️  {msg}\033[0m")

def log_error(msg):
    print(f"\033[91m❌ {msg}\033[0m")

def log_section(title):
    print(f"\n\033[95m🔷 --- {title} --- 🔷\033[0m")

def log_debug_object(label, obj, max_chars=800):
    """
    Pretty-print objects (payloads, errors, responses)
    truncated if too large.
    """
    try:
        text = json.dumps(obj, indent=2, ensure_ascii=False)
    except:
        text = str(obj)

    if len(text) > max_chars:
        text = text[:max_chars] + " ... (truncated)"

    print(f"\033[90m📦 {label}:\n{text}\033[0m")


# ======================================================================
#                        EMAIL PROCESSOR
# ======================================================================

class EmailProcessor:

    def __init__(self):
        self.filter = AdvancedEmailFilter()
        self.thread_manager = ThreadManager()
        self.attachment_service = AttachmentService()
        self.email_cleaner = EmailCleaner()
        self.thread_repo = ThreadRepository()

        base = os.getenv("AUTOMATION_API_URL", "http://automations:8010/")
        self.automation_api_url = base.rstrip("/") + "/workflows/process-email"

        log_info(f"[INIT] Automation API URL set to: {self.automation_api_url}")

    # ==================================================================
    #                 MAIN EMAIL PROCESSING PIPELINE
    # ==================================================================
    async def process_message(self, email_data: dict) -> Optional[dict]:
        log_section("PROCESSING MESSAGE")

        try:
            log_info(f"Processing message_id={email_data.get('message_id')} from={email_data.get('from')}")

            # Clean body
            email_data = self.email_cleaner.clean_email_content(email_data)

            # Filter
            filter_result = await self.filter.process_message(email_data)
            if not filter_result:
                log_warn("Message filtered out by AdvancedEmailFilter")
                return None

            action = filter_result.get("action")
            summarizer_only = filter_result.get("summarizer_only", False)

            email_data["action"] = action
            email_data["summarizer_only"] = summarizer_only

            log_info(f"Filter decided action: {action}")

            # ----------------------------------------------------------
            # SUMMARIZER ONLY WORKFLOW
            # ----------------------------------------------------------
            if action == "send_to_summarizer":
                log_section("SUMMARIZER ONLY")
                needs_ai = filter_result.get("needs_ai", False)

                if not needs_ai:
                    log_warn("Marked for summarizer but no AI processing required")
                    return {"status": "skipped", "reason": "no_ai_needed_for_summarizer", "needs_ai_processing": False}

                reply_to_id = email_data.get("reply_to_id")
                box_email = email_data.get("user_email")
                thread_id = None

                if reply_to_id and reply_to_id.lower() != "no":
                    thread = self.thread_repo.find_thread_by_reply_to(reply_to_id, box_email)
                    if thread:
                        thread_id = thread.get("thread_id")
                        log_success(f"Found thread_id={thread_id} for summarizer reply")
                    else:
                        log_warn(f"No thread found for reply_to_id={reply_to_id}")

                if not thread_id:
                    log_error("Summarizer requested but thread_id missing — skipping.")
                    return {"status": "skipped", "reason": "no_thread_found_for_summarizer"}

                # Attachments
                processed_attachments = []
                if email_data.get("attachments"):
                    try:
                        processed_attachments = await self.attachment_service.process_attachments(email_data, thread_id)
                    except Exception as e:
                        log_error(f"Failed to process attachments: {e}")

                payload = self._prepare_automation_payload(email_data, {"thread_id": thread_id, "box_email": box_email}, processed_attachments)

                try:
                    await self.send_to_automation(payload)
                except Exception as e:
                    log_error(f"Could not send summarizer payload: {e}")

                return {"status": "sent_to_summarizer", "thread_id": thread_id}

            # ----------------------------------------------------------
            # NEW THREAD CREATED
            # ----------------------------------------------------------
            if action == "thread_created":
                log_section("THREAD CREATED")

                thread_data = filter_result.get("thread", {})
                thread_id = thread_data.get("thread_id")
                needs_ai = filter_result.get("needs_ai", False)

                # Attachments
                processed_attachments = []
                if email_data.get("attachments"):
                    try:
                        processed_attachments = await self.attachment_service.process_attachments(email_data, thread_id)
                        thread_data["attachments_processed"] = len(processed_attachments)
                    except Exception as e:
                        log_error(f"Attachment processing error: {e}")
                        thread_data["attachments_processed"] = 0

                if needs_ai:
                    log_success(f"Thread {thread_id} requires AI processing")

                    payload = self._prepare_automation_payload(email_data, thread_data, processed_attachments)
                    await self.send_to_automation(payload)
                else:
                    log_info(f"Thread {thread_id} created but no AI processing required")

                return {"status": "thread_created", "thread_id": thread_id}

            # ----------------------------------------------------------
            # THREAD UPDATED
            # ----------------------------------------------------------
            if action == "thread_updated":
                log_section("THREAD UPDATED")

                thread_id = filter_result.get("thread_id")
                processed_attachments = []

                if email_data.get("attachments"):
                    try:
                        processed_attachments = await self.attachment_service.process_attachments(email_data, thread_id)
                    except Exception as e:
                        log_error(f"Attachment processing error: {e}")

                payload = self._prepare_automation_payload(email_data, {"thread_id": thread_id, "box_email": email_data.get("user_email")}, processed_attachments)
                await self.send_to_automation(payload)

                return {"status": "thread_updated", "thread_id": thread_id}

            # ----------------------------------------------------------
            # HUMAN RESPONSE
            # ----------------------------------------------------------
            if action == "human_response_marked":
                log_section("HUMAN RESPONSE REQUIRED")
                thread_id = filter_result.get("thread_id")
                return {"status": "human_response_needed", "thread_id": thread_id}

            # ----------------------------------------------------------
            # SKIPPED
            # ----------------------------------------------------------
            if action == "skip":
                log_warn(f"Message skipped: {filter_result.get('reason')}")
                return {"status": "skipped", "reason": filter_result.get("reason")}

            log_warn(f"Unknown action returned by filter: {action}")
            return None

        except Exception as e:
            log_error("Fatal error in EmailProcessor:")
            traceback.print_exc()
            return None

    # ==================================================================
    #                    SEND TO AUTOMATION SERVICE
    # ==================================================================
    async def send_to_automation(self, automation_payload: dict) -> bool:
        log_section("SENDING TO AUTOMATION")

        log_debug_object("Payload", automation_payload)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.automation_api_url,
                    json=automation_payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:

                    text = await resp.text()

                    if resp.status == 200:
                        log_success("Automation API accepted payload")
                        return True

                    log_error(f"Automation API returned error {resp.status}")
                    print(text)
                    return False

        except aiohttp.ClientError as e:
            log_error(f"HTTP client error: {e}")
            return False
        except Exception as e:
            log_error(f"Unexpected send_to_automation error: {e}")
            traceback.print_exc()
            return False

    # ==================================================================
    #                  PREPARE AUTOMATION PAYLOAD
    # ==================================================================
    def _prepare_automation_payload(self, email_data: dict, thread_data: dict, processed_attachments: list) -> dict:

        attachment_ids = [a["attachment_id"] for a in processed_attachments if a.get("attachment_id")]

        thread_id = thread_data.get("thread_id")
        category = None
        subcategory = None
        extended_summary = None
        has_attachments = len(attachment_ids) > 0

        # Load full thread metadata
        if thread_id:
            try:
                full = self.thread_repo.get_thread_by_id(thread_id)
                if full:
                    category = full.get("category")
                    subcategory = full.get("subcategory")
                    extended_summary = full.get("extended_summary")
                    has_attachments = full.get("has_attachments", has_attachments)
            except Exception as e:
                log_warn(f"Could not load thread metadata: {e}")

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

            "body": email_data.get("body_text", email_data.get("body", "")),
            "provider": email_data.get("provider"),

            "subcategory": subcategory,
            "category": category,
            "extended_summary": extended_summary,

            "attachment_ids": attachment_ids,
            "has_attachments": has_attachments,

            "no_reply": email_data.get("no_reply", False),
            "action": email_data.get("action"),
            "summarizer_only": email_data.get("summarizer_only", False),
            "original_thread_id": email_data.get("original_thread_id"),
        }

        return payload
