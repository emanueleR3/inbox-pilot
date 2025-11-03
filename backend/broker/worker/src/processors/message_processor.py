"""
Main email processor that orchestrates filtering, thread management, and AI workflow routing.
This is the central processing hub for all email messages.
"""

from src.filters.advanced_filter import AdvancedEmailFilter
from src.managers.thread_manager import ThreadManager, ThreadInfo
from typing import Optional


class EmailProcessor:
    """
    Central email processor that coordinates all email processing operations.
    Handles filtering, thread management, database operations, and AI workflow routing.
    """
    
    def __init__(self):
        self.filter = AdvancedEmailFilter()
        self.thread_manager = ThreadManager()
    
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
            
            # Step 1: Apply advanced filtering
            filter_result = await self.filter.process_message(email_data)
            
            if not filter_result:
                print(f"🚫 [PROCESSOR] Message filtered out")
                return None
            
            # Step 2: Handle the result based on filter outcome
            action = filter_result.get("action")
            
            if action == "thread_created":
                # New thread was created
                thread_data = filter_result.get("thread", {})
                needs_ai = filter_result.get("needs_ai", False)
                
                if needs_ai:
                    print(f"🤖 [PROCESSOR] Thread created from external user - sending to AI workflow")
                    print(f"🧵 Thread ID: {thread_data.get('thread_id')}")
                    print(f"📧 Subject: {thread_data.get('subject')}")
                    print(f"👤 Sender: {thread_data.get('sender_email')}")
                    print(f"📮 Mailbox: {thread_data.get('box_email')}")
                    # TODO: Send to AI workflow
                else:
                    print(f"👤 [PROCESSOR] Thread created from user - no AI processing needed")
                
                return {
                    "status": "thread_created",
                    "thread_id": thread_data.get("thread_id"),
                    "needs_ai_processing": needs_ai
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
                print(f"📝 [PROCESSOR] Thread {thread_id} updated with reply - sending to AI workflow")
                # TODO: Send to AI workflow for processing the new message
                return {
                    "status": "thread_updated",
                    "thread_id": thread_id,
                    "needs_ai_processing": True
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
    
    async def should_skip_message(self, email_data: dict) -> bool:
        """
        Determines if message should be skipped using advanced filtering.
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            True if message should be skipped
        """
        # TODO: Implement skip logic
        pass
    
    async def save_to_database(self, email_data: dict) -> ThreadInfo:
        """
        Saves message to database and returns thread information.
        
        Args:
            email_data: Email data from listeners
            
        Returns:
            ThreadInfo with processing requirements
        """
        # TODO: Implement database save logic
        pass
    
    async def route_to_ai_workflow(self, email_data: dict, thread_info: ThreadInfo) -> bool:
        """
        Routes message to appropriate AI workflow if needed.
        
        Args:
            email_data: Email data from listeners
            thread_info: Thread information and processing requirements
            
        Returns:
            True if successfully routed to AI workflow
        """
        # TODO: Implement AI workflow routing
        pass
    
    async def handle_human_response(self, email_data: dict, thread_info: ThreadInfo) -> bool:
        """
        Handles human response notifications and thread updates.
        
        Args:
            email_data: Email data from listeners
            thread_info: Thread information
            
        Returns:
            True if human response handled successfully
        """
        # TODO: Implement human response handling
        pass