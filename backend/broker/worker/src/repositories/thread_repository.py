"""
Thread repository for database operations on email threads.
Handles all database interactions for the threads table.
"""

import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from src.utils.db_client import get_supabase_client


class ThreadRepository:
    """
    Repository for thread database operations.
    Handles creation, retrieval, and updates for email threads.
    """
    
    def __init__(self):
        # Initialize database connection
        self.supabase = get_supabase_client()
    
    def create_thread(
        self,
        started_at: datetime = None,
        history: List[str] = None,
        subject: str = None,
        sender_email: str = None,
        cc_emails: List[str] = None,
        summary: str = None,
        last_message_id: str = None,
        last_message_at: datetime = None,
        attachment_emails_id: List[str] = None,
        category: str = None,
        human_response: bool = None,
        last_sender_email: str = None,
        box_email: str = None
    ) -> dict:
        """
        Creates a new thread in the database.
        All parameters are optional and will be set to None if not provided.
        Similar to create_subscription_service pattern.
        
        Args:
            started_at: When the thread started
            history: Array of message IDs in the thread
            subject: Thread subject
            sender_email: Email of the thread initiator
            cc_emails: Array of CC email addresses
            summary: Thread summary
            last_message_id: ID of the last message
            last_message_at: Timestamp of last message
            attachment_emails_id: Array of message IDs with attachments
            category: Thread category
            human_response: Whether human response is needed
            last_sender_email: Email of last sender
            box_email: Email of the mailbox being monitored
            
        Returns:
            dict: The created thread record if successful, None if error
        """
        try:
            # Validate that box_email exists in subscription_services if provided
            if box_email:
                subscription_check = self.supabase.table("subscription_services").select("email").eq("email", box_email).execute()
                if not subscription_check.data:
                    print(f"❌ [THREAD] Box email {box_email} not found in subscription_services")
                    return None
            
            data = {
                "started_at": started_at.isoformat() if started_at else None,
                "history": history if history is not None else [],
                "subject": subject,
                "sender_email": sender_email,
                "cc_emails": cc_emails if cc_emails is not None else [],
                "summary": summary,  # Can be None now
                "last_message_id": last_message_id,
                "last_message_at": last_message_at.isoformat() if last_message_at else None,
                "attachment_emails_id": attachment_emails_id if attachment_emails_id is not None else [],
                "category": category if category is not None else "",  # Default to empty string if not provided
                "human_response": human_response if human_response is not None else False,
                "last_sender_email": last_sender_email,
                "box_email": box_email
            }
            
            # Remove keys with None values to allow database defaults
            data = {k: v for k, v in data.items() if v is not None}
            
            # Insert record into database
            response = self.supabase.table("threads").insert(data).execute()
            
            if response.data:
                created_thread = response.data[0]
                print(f"🗂️ [THREAD] Thread created successfully with ID: {created_thread.get('thread_id')}")
                return created_thread
            else:
                print(f"❌ [THREAD] No data returned from database insert")
                return None
            
        except Exception as e:
            print(f"❌ Error creating thread: {e}")
            return None
    
    def get_thread_by_id(self, thread_id: str) -> Optional[dict]:
        """
        Retrieves a thread by its ID.
        
        Args:
            thread_id: Thread ID to retrieve
            
        Returns:
            Thread record if found, None otherwise
        """
        try:
            # Get thread from database
            response = self.supabase.table("threads").select("*").eq("thread_id", thread_id).execute()
            
            if response.data:
                print(f"🔍 [THREAD] Thread found: {thread_id}")
                return response.data[0]
            else:
                print(f"🔍 [THREAD] Thread not found: {thread_id}")
                return None
            
        except Exception as e:
            print(f"❌ Error retrieving thread {thread_id}: {e}")
            return None
    
    def update_thread_history(self, thread_id: str, new_message_id: str) -> bool:
        """
        Adds a new message ID to the thread history.
        
        Args:
            thread_id: Thread ID to update
            new_message_id: Message ID to add to history
            
        Returns:
            True if updated successfully
        """
        try:
            # Get current thread data
            current_thread = self.get_thread_by_id(thread_id)
            if not current_thread:
                print(f"❌ [THREAD] Thread {thread_id} not found for history update")
                return False
            
            # Get current history and append new message
            current_history = current_thread.get("history", [])
            if new_message_id not in current_history:
                updated_history = current_history + [new_message_id]
                
                # Update the thread
                response = self.supabase.table("threads").update({
                    "history": updated_history,
                    "last_message_id": new_message_id,
                    "last_message_at": datetime.now(timezone.utc).isoformat()
                }).eq("thread_id", thread_id).execute()
                
                if response.data:
                    print(f"📝 [THREAD] Message {new_message_id} added to thread {thread_id} history")
                    return True
                else:
                    print(f"❌ [THREAD] Failed to update thread {thread_id} history")
                    return False
            else:
                print(f"⚠️ [THREAD] Message {new_message_id} already exists in thread {thread_id} history")
                return True
            
        except Exception as e:
            print(f"❌ Error updating thread history: {e}")
            return False
    
    def find_thread_by_reply_to(self, reply_to_id: str, box_email: str = None) -> Optional[dict]:
        """
        Finds a thread that contains the replied-to message ID in its history.
        Optionally filters by box_email for optimization.
        
        Args:
            reply_to_id: Message ID that this email is replying to
            box_email: Optional box email to filter threads first
            
        Returns:
            Thread record if found, None otherwise
        """
        try:
            query = self.supabase.table("threads").select("*")
            
            # Pre-filter by box_email for optimization
            if box_email:
                query = query.eq("box_email", box_email)
            
            # Search for threads where history array contains the reply_to_id
            response = query.contains("history", [reply_to_id]).execute()
            
            if response.data:
                thread = response.data[0]  # Return first match
                print(f"🔍 [THREAD] Found thread {thread.get('thread_id')} containing message: {reply_to_id}")
                return thread
            else:
                print(f"🔍 [THREAD] No thread found containing message: {reply_to_id}")
                return None
            
        except Exception as e:
            print(f"❌ Error finding thread by reply_to: {e}")
            return None
    
    def is_message_in_thread_history(self, thread_id: str, message_id: str) -> bool:
        """
        Checks if a message ID is already present in a thread's history.
        
        Args:
            thread_id: Thread ID to check
            message_id: Message ID to look for
            
        Returns:
            True if message is in history, False otherwise
        """
        try:
            response = self.supabase.table("threads").select("history").eq("thread_id", thread_id).execute()
            
            if response.data:
                history = response.data[0].get("history", [])
                is_present = message_id in history
                print(f"🔍 [THREAD] Message {message_id} {'found' if is_present else 'not found'} in thread {thread_id} history")
                return is_present
            else:
                print(f"❌ [THREAD] Thread {thread_id} not found for history check")
                return False
            
        except Exception as e:
            print(f"❌ Error checking message in thread history: {e}")
            return False
    
    def update_thread_with_new_message(self, thread_id: str, message_id: str, message_timestamp: datetime, 
                                     sender_email: str, cc_emails: List[str] = None) -> bool:
        """
        Updates a thread with a new message (for received emails).
        
        Args:
            thread_id: Thread ID to update
            message_id: New message ID to add
            message_timestamp: Timestamp of the new message
            sender_email: Email of the sender
            cc_emails: Optional CC emails to add
            
        Returns:
            True if updated successfully
        """
        try:
            # Get current thread data
            current_thread = self.get_thread_by_id(thread_id)
            if not current_thread:
                print(f"❌ [THREAD] Thread {thread_id} not found for message update")
                return False
            
            # Prepare updated data
            current_history = current_thread.get("history", [])
            updated_history = current_history + [message_id]
            
            # Merge CC emails if provided
            current_cc_emails = current_thread.get("cc_emails", [])
            updated_cc_emails = current_cc_emails.copy()
            if cc_emails:
                for cc in cc_emails:
                    if cc not in updated_cc_emails:
                        updated_cc_emails.append(cc)
            
            update_data = {
                "history": updated_history,
                "last_message_id": message_id,
                "last_message_at": message_timestamp.isoformat(),
                "last_sender_email": sender_email,
                "cc_emails": updated_cc_emails
            }
            
            # Update the thread
            response = self.supabase.table("threads").update(update_data).eq("thread_id", thread_id).execute()
            
            if response.data:
                print(f"📝 [THREAD] Thread {thread_id} updated with new message {message_id}")
                return True
            else:
                print(f"❌ [THREAD] Failed to update thread {thread_id}")
                return False
            
        except Exception as e:
            print(f"❌ Error updating thread with new message: {e}")
            return False
    
    def set_human_response_needed(self, thread_id: str, message_id: str = None, message_timestamp: datetime = None) -> bool:
        """
        Sets human_response to True for a thread (when user sends a reply).
        Optionally adds the user's message to the thread history.
        
        Args:
            thread_id: Thread ID to update
            message_id: Optional message ID to add to history
            message_timestamp: Optional timestamp of the message
            
        Returns:
            True if updated successfully
        """
        try:
            update_data = {"human_response": True}
            
            # If message details provided, update history and timestamps
            if message_id and message_timestamp:
                # Get current thread data
                current_thread = self.get_thread_by_id(thread_id)
                if current_thread:
                    current_history = current_thread.get("history", [])
                    if message_id not in current_history:
                        updated_history = current_history + [message_id]
                        update_data.update({
                            "history": updated_history,
                            "last_message_id": message_id,
                            "last_message_at": message_timestamp.isoformat()
                        })
            
            response = self.supabase.table("threads").update(update_data).eq("thread_id", thread_id).execute()
            
            if response.data:
                print(f"👤 [THREAD] Thread {thread_id} marked as needing human response")
                if message_id:
                    print(f"📝 [THREAD] User message {message_id} added to thread {thread_id} history")
                return True
            else:
                print(f"❌ [THREAD] Failed to update human_response for thread {thread_id}")
                return False
            
        except Exception as e:
            print(f"❌ Error setting human response: {e}")
            return False