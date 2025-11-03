"""
Advanced email filtering logic.
Handles complex filtering rules that go beyond the basic pre-filtering done in listeners.
"""

from datetime import datetime, timezone
from typing import Optional, List
from src.repositories.thread_repository import ThreadRepository


class AdvancedEmailFilter:
    """
    Handles advanced email filtering logic centralized in the broker.
    This includes AI-generated detection, duplicate checking, and complex business rules.
    """
    
    def __init__(self):
        self.thread_repo = ThreadRepository()
    
    async def process_message(self, email_data: dict) -> Optional[dict]:
        """
        Main processing method that applies all filters and creates threads if needed.
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            Processing result or None if message should be skipped
        """
        try:
            # Check for duplicate message_id first
            message_id = email_data.get("message_id")
            box_email = email_data.get("user_email")
            
            if message_id and self.thread_repo.message_id_exists(message_id, box_email):
                print(f"🚫 [FILTER] Duplicate message detected - message_id {message_id} already processed")
                return None
            
            # Apply the first filter: new conversation from sent messages
            if await self._is_new_conversation_from_user(email_data):
                thread_result = await self._create_new_thread_from_sent(email_data)
                if thread_result:
                    print(f"✅ [FILTER] Created new thread for user-initiated conversation")
                    return {"action": "thread_created", "thread": thread_result, "needs_ai": False}
                else:
                    print(f"❌ [FILTER] Failed to create new thread")
                    return None
            
            # Apply the second filter: new conversation from external users
            if await self._is_new_conversation_from_external(email_data):
                thread_result = await self._create_new_thread_from_external(email_data)
                if thread_result:
                    print(f"✅ [FILTER] Created new thread for external-initiated conversation")
                    return {"action": "thread_created", "thread": thread_result, "needs_ai": True}
                else:
                    print(f"❌ [FILTER] Failed to create new thread from external")
                    return None
            
            # Apply the third filter: replies to existing threads
            if await self._is_reply_to_existing_thread(email_data):
                reply_result = await self._handle_reply_to_thread(email_data)
                if reply_result:
                    action = reply_result.get("action")
                    if action == "duplicate_skipped":
                        print(f"🔄 [FILTER] Duplicate message skipped")
                        return {"action": "skip", "reason": "duplicate"}
                    elif action == "thread_updated":
                        print(f"✅ [FILTER] Thread updated with reply")
                        return {"action": "thread_updated", "thread_id": reply_result.get("thread_id"), "needs_ai": True}
                    elif action == "human_response_set":
                        print(f"👤 [FILTER] Human response marked for thread")
                        return {"action": "human_response_marked", "thread_id": reply_result.get("thread_id"), "needs_ai": False}
                else:
                    print(f"❌ [FILTER] Failed to handle reply")
                    return None
            
            # TODO: Add more filters here
            # - Check for replies to existing threads
            # - Check for duplicates
            # - Check for AI-generated messages
            
            print(f"📋 [FILTER] Message passed all filters, ready for further processing")
            return {"action": "process", "needs_ai": True}
            
        except Exception as e:
            print(f"❌ [FILTER] Error processing message: {e}")
            return None
    
    async def _is_reply_to_existing_thread(self, email_data: dict) -> bool:
        """
        Checks if this is a reply to an existing thread.
        Criteria: reply_to_id != "no" and not empty
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            True if this is a reply to existing thread
        """
        reply_to_id = email_data.get("reply_to_id", "").lower()
        
        result = reply_to_id != "no" and reply_to_id.strip() != ""
        
        if result:
            print(f"🔗 [FILTER] Detected reply to message: {reply_to_id}")
        
        return result
    
    async def _handle_reply_to_thread(self, email_data: dict) -> Optional[dict]:
        """
        Handles replies to existing threads.
        
        Logic:
        1. Find thread containing reply_to_id in history
        2. Check if current message_id already exists in thread history (duplicate)
        3. If not duplicate:
           - If is_sent=True: set human_response=True
           - If is_sent=False: update thread with new message data
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            Processing result or None if failed
        """
        try:
            reply_to_id = email_data.get("reply_to_id")
            message_id = email_data.get("message_id")
            box_email = email_data.get("user_email")
            is_sent = email_data.get("is_sent", False)
            
            # Step 1: Find thread containing reply_to_id
            thread = self.thread_repo.find_thread_by_reply_to(reply_to_id, box_email)
            if not thread:
                print(f"❌ [FILTER] No thread found for reply_to_id: {reply_to_id}")
                return None
            
            thread_id = thread.get("thread_id")
            
            # Step 2: Check if message already exists in thread history
            if self.thread_repo.is_message_in_thread_history(thread_id, message_id):
                print(f"🔄 [FILTER] Duplicate message {message_id} found in thread {thread_id}")
                return {"action": "duplicate_skipped", "thread_id": thread_id}
            
            # Step 3: Handle based on is_sent
            if is_sent:
                # User sent a reply - mark as needing human response and add to history
                timestamp_str = email_data.get("timestamp") or email_data.get("date")
                message_datetime = self._parse_timestamp(timestamp_str)
                sender_email = self._extract_email_address(email_data.get("from"))
                
                if self.thread_repo.set_human_response_needed(thread_id, message_id, message_datetime, sender_email):
                    print(f"👤 [FILTER] Human response set for thread {thread_id}")
                    # TODO: notifica, aggiornare summary e category
                    return {"action": "human_response_set", "thread_id": thread_id}
                else:
                    print(f"❌ [FILTER] Failed to set human response for thread {thread_id}")
                    return None
            else:
                # External reply - update thread with new message
                timestamp_str = email_data.get("timestamp") or email_data.get("date")
                message_datetime = self._parse_timestamp(timestamp_str)
                sender_email = self._extract_email_address(email_data.get("from"))
                cc_emails = self._extract_cc_emails(email_data.get("cc"))
                
                if self.thread_repo.update_thread_with_new_message(
                    thread_id, message_id, message_datetime, sender_email, cc_emails
                ):
                    print(f"📝 [FILTER] Thread {thread_id} updated with new message {message_id}")
                    return {"action": "thread_updated", "thread_id": thread_id}
                else:
                    print(f"❌ [FILTER] Failed to update thread {thread_id}")
                    return None
                    
        except Exception as e:
            print(f"❌ [FILTER] Error handling reply to thread: {e}")
            return None
    
    async def _is_new_conversation_from_external(self, email_data: dict) -> bool:
        """
        Checks if this is a new conversation started by an external user.
        Criteria: is_sent=False AND reply_to_id="no"
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            True if this is a new conversation from external user
        """
        is_sent = email_data.get("is_sent", False)
        reply_to_id = email_data.get("reply_to_id", "").lower()
        
        result = not is_sent and reply_to_id == "no"
        
        if result:
            print(f"🎯 [FILTER] Detected new conversation from external user: {email_data.get('from')} -> {email_data.get('to')}")
        
        return result
    
    async def _is_new_conversation_from_user(self, email_data: dict) -> bool:
        """
        Checks if this is a new conversation started by the user.
        Criteria: is_sent=True AND reply_to_id="no"
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            True if this is a new conversation from user
        """
        is_sent = email_data.get("is_sent", False)
        reply_to_id = email_data.get("reply_to_id", "").lower()
        
        result = is_sent and reply_to_id == "no"
        
        if result:
            print(f"🎯 [FILTER] Detected new conversation from user: {email_data.get('from')} -> {email_data.get('to')}")
        
        return result
    
    async def _create_new_thread_from_external(self, email_data: dict) -> Optional[dict]:
        """
        Creates a new thread for an external user-initiated conversation.
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            Created thread data or None if failed
        """
        try:
            # Parse timestamp - handle different formats from different providers
            timestamp_str = email_data.get("timestamp") or email_data.get("date")
            message_datetime = self._parse_timestamp(timestamp_str)
            
            # Extract CC emails if present
            cc_emails = self._extract_cc_emails(email_data.get("cc"))
            
            # For external emails, sender_email is the 'from' field, not user_email
            sender_email = self._extract_email_address(email_data.get("from"))
            
            # Create the thread with minimal data as requested
            thread_data = self.thread_repo.create_thread(
                started_at=message_datetime,
                history=[email_data.get("message_id")],  # Start with this message
                subject=email_data.get("subject"),
                sender_email=sender_email,  # External user who sent the email
                cc_emails=cc_emails,
                summary=None,  # Will be filled later by AI
                last_message_id=email_data.get("message_id"),
                last_message_at=message_datetime,
                attachment_emails_id=None,  # Set to None as requested
                category=None,  # Set to None as requested
                human_response=False,  # External user initiated, no human response yet
                last_sender_email=sender_email,
                box_email=email_data.get("user_email")  # Email of the monitored mailbox
            )
            
            return thread_data
            
        except Exception as e:
            print(f"❌ [FILTER] Error creating new thread from external: {e}")
            return None
    
    async def _create_new_thread_from_sent(self, email_data: dict) -> Optional[dict]:
        """
        Creates a new thread for a user-initiated conversation.
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            Created thread data or None if failed
        """
        try:
            # Parse timestamp - handle different formats from different providers
            timestamp_str = email_data.get("timestamp") or email_data.get("date")
            message_datetime = self._parse_timestamp(timestamp_str)
            
            # Extract CC emails if present
            cc_emails = self._extract_cc_emails(email_data.get("cc"))
            
            # Create the thread
            thread_data = self.thread_repo.create_thread(
                started_at=message_datetime,
                history=[email_data.get("message_id")],  # Start with this message
                subject=email_data.get("subject"),
                sender_email=email_data.get("user_email"),  # User who sent the email
                cc_emails=cc_emails,
                summary=None,  # Will be filled later by AI
                last_message_id=email_data.get("message_id"),
                last_message_at=message_datetime,
                attachment_emails_id=None,  # No attachments for now
                category="STARTED_BY_HUMAN",  # Category for user-initiated conversations
                human_response=True,  # User initiated, so it's a human response
                last_sender_email=self._extract_email_address(email_data.get("user_email")),
                box_email=email_data.get("user_email")  # Email of the monitored mailbox
            )
            
            return thread_data
            
        except Exception as e:
            print(f"❌ [FILTER] Error creating new thread: {e}")
            return None
    
    def _extract_email_address(self, email_field: str) -> str:
        """
        Extracts the email address from various formats.
        
        Handles formats like:
        - "email@domain.com"
        - "Name Surname <email@domain.com>"
        - "Name Surname<email@domain.com>"
        
        Args:
            email_field: Email field that may contain name and email
            
        Returns:
            Clean email address
        """
        if not email_field:
            return ""
        
        # If there are angle brackets, extract email from within them
        if '<' in email_field and '>' in email_field:
            start = email_field.find('<')
            end = email_field.find('>')
            if start != -1 and end != -1 and end > start:
                return email_field[start + 1:end].strip()
        
        # If no brackets, assume the whole field is the email
        return email_field.strip()
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parses timestamp from different email providers into datetime object.
        
        Args:
            timestamp_str: Timestamp string from email data
            
        Returns:
            datetime object
        """
        if not timestamp_str:
            return datetime.now(timezone.utc)
        
        try:
            # Handle different timestamp formats
            if isinstance(timestamp_str, str):
                # Gmail internal date (milliseconds since epoch)
                if timestamp_str.isdigit():
                    timestamp_ms = int(timestamp_str)
                    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
                # ISO format
                elif 'T' in timestamp_str:
                    if timestamp_str.endswith('Z'):
                        timestamp_str = timestamp_str[:-1] + '+00:00'
                    return datetime.fromisoformat(timestamp_str)
            
            # Fallback to current time
            return datetime.now(timezone.utc)
            
        except Exception as e:
            print(f"⚠️ [FILTER] Error parsing timestamp {timestamp_str}: {e}")
            return datetime.now(timezone.utc)
    
    def _extract_cc_emails(self, cc_header: str) -> List[str]:
        """
        Extracts CC email addresses from the CC header.
        
        Args:
            cc_header: CC header string
            
        Returns:
            List of email addresses
        """
        if not cc_header:
            return []
        
        try:
            # Simple extraction - split by comma and clean up
            emails = [email.strip() for email in cc_header.split(',')]
            # TODO: Add more sophisticated email extraction if needed
            return [email for email in emails if email and '@' in email]
        except Exception as e:
            print(f"⚠️ [FILTER] Error extracting CC emails from {cc_header}: {e}")
            return []
    
    async def should_skip_message(self, email_data: dict) -> bool:
        """
        Determines if a message should be skipped from processing.
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            True if message should be skipped, False if it should be processed
        """
        # TODO: Implement advanced filtering logic
        pass
    
    async def is_ai_generated_message(self, email_data: dict) -> bool:
        """
        Detects if a message was generated by AI.
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            True if message is AI-generated
        """
        # TODO: Implement AI detection logic
        pass
    
    async def is_duplicate_in_thread(self, email_data: dict) -> bool:
        """
        Checks if message is a duplicate within the thread history.
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            True if message is a duplicate
        """
        # TODO: Implement duplicate detection logic
        pass
    
    async def should_trigger_human_response(self, email_data: dict) -> bool:
        """
        Determines if message should trigger human response notification.
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            True if human response is needed
        """
        # TODO: Implement human response detection logic
        pass