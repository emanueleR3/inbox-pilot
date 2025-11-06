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
        extended_summary: str = None,
        last_message_id: str = None,
        last_message_at: datetime = None,
        has_attachments: bool = False,
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
            extended_summary: Extended thread summary (più dettagliato)
            last_message_id: ID of the last message
            last_message_at: Timestamp of last message
            has_attachments: Boolean flag indicating if thread has attachments
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
                "extended_summary": extended_summary,  # Can be None (default)
                "last_message_id": last_message_id,
                "last_message_at": last_message_at.isoformat() if last_message_at else None,
                "has_attachments": has_attachments,
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
                                     sender_email: str, cc_emails: List[str] = None, reply_to_id: str = None, 
                                     has_new_attachments: bool = False) -> bool:
        """
        Updates a thread with a new message (for received emails).
        Ensures reply_to_id is in history before adding the new message_id.
        
        Args:
            thread_id: Thread ID to update
            message_id: New message ID to add
            message_timestamp: Timestamp of the new message
            sender_email: Email of the sender
            cc_emails: Optional CC emails to add
            reply_to_id: Optional reply-to message ID to ensure is in history
            has_new_attachments: If True, sets has_attachments flag to True for the thread
            
        Returns:
            True if updated successfully
        """
        try:
            # Get current thread data
            current_thread = self.get_thread_by_id(thread_id)
            if not current_thread:
                print(f"❌ [THREAD] Thread {thread_id} not found for message update")
                return False
            
            # Prepare updated history with reply_to_id check
            current_history = current_thread.get("history", [])
            updated_history = current_history.copy()
            
            # Ensure reply_to_id is in history (if provided and missing)
            if reply_to_id and reply_to_id != "no" and reply_to_id not in updated_history:
                print(f"⚠️ [THREAD] Reply-to message {reply_to_id} missing from history, adding it")
                updated_history.append(reply_to_id)
            
            # Add new message_id if not already present
            if message_id not in updated_history:
                updated_history.append(message_id)
            else:
                print(f"🔄 [THREAD] Message {message_id} already in history for thread {thread_id}")
            
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
            
            # If this message has attachments, set has_attachments to True
            if has_new_attachments:
                update_data["has_attachments"] = True
                print(f"📎 [THREAD] Setting has_attachments=True for thread {thread_id} due to new attachments")
            
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
    
    def set_human_response_needed(self, thread_id: str, message_id: str = None, message_timestamp: datetime = None, sender_email: str = None) -> bool:
        """
        Sets human_response to True for a thread (when user sends a reply).
        Optionally adds the user's message to the thread history.
        
        Args:
            thread_id: Thread ID to update
            message_id: Optional message ID to add to history
            message_timestamp: Optional timestamp of the message
            sender_email: Optional sender email to update last_sender_email
            
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
                        
                        # Update last_sender_email if provided
                        if sender_email:
                            update_data["last_sender_email"] = sender_email
            
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

    def message_id_exists(self, message_id: str, box_email: str = None) -> bool:
        """
        Check if a message_id already exists in any thread.
        
        Args:
            message_id: The message ID to check
            box_email: Optional box email to limit search scope
            
        Returns:
            bool: True if message_id exists, False otherwise
        """
        try:
            # Simple approach: just check last_message_id for now
            # Array search can be complex with Supabase syntax
            query = self.supabase.table("threads").select("thread_id, last_message_id, history")
            
            if box_email:
                response = query.eq("box_email", box_email).execute()
            else:
                response = query.execute()
            
            # Check manually in the results
            for thread in response.data:
                if (thread.get("last_message_id") == message_id or 
                    (thread.get("history") and message_id in thread.get("history", []))):
                    print(f"🔍 [THREAD] Message ID {message_id} already exists in thread: {thread['thread_id']}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking message_id existence: {e}")
            return False
    
    def find_thread_by_reply_to_global(self, reply_to_id: str) -> Optional[dict]:
        """
        Cerca un thread contenente reply_to_id in TUTTE le mailboxes.
        Usato quando la ricerca locale fallisce per gestire conversazioni cross-mailbox.
        
        Args:
            reply_to_id: Message ID to search for in thread histories
            
        Returns:
            Thread data if found, None otherwise
        """
        try:
            # Cerca in tutti i thread, senza filtro box_email
            response = self.supabase.table("threads").select("*").execute()
            
            # Controlla manualmente nei risultati (stesso approccio di message_id_exists)
            for thread in response.data:
                history = thread.get("history", [])
                last_message_id = thread.get("last_message_id")
                
                if (last_message_id == reply_to_id or 
                    (history and reply_to_id in history)):
                    print(f"🌐 [THREAD] Found thread {thread.get('thread_id')} in mailbox {thread.get('box_email')} for reply: {reply_to_id}")
                    return thread
            
            return None
            
        except Exception as e:
            print(f"❌ Error in global thread search: {e}")
            return None
    
    def find_or_create_local_thread_for_conversation(self, reply_to_id: str, box_email: str, 
                                                   message_id: str, message_timestamp: datetime,
                                                   subject: str, sender_email: str, cc_emails: List[str] = None) -> Optional[dict]:
        """
        Trova o crea un thread locale per la mailbox corrente che sia collegato alla conversazione.
        Cerca prima un thread locale che contenga qualsiasi message_id della conversazione cross-mailbox.
        
        Args:
            reply_to_id: Message ID to which this is a reply
            box_email: Current mailbox email
            message_id: Current message ID
            message_timestamp: Current message timestamp
            subject: Current message subject
            sender_email: Current message sender
            cc_emails: Current message CC emails
            
        Returns:
            Thread data for the local mailbox, either found or created
        """
        try:
            # Prima, trova il thread cross-mailbox per ottenere la history completa
            cross_thread = self.find_thread_by_reply_to_global(reply_to_id)
            if not cross_thread:
                print(f"❌ [THREAD] No cross-mailbox thread found for reply_to_id: {reply_to_id}")
                return None
                
            cross_history = cross_thread.get("history", [])
            cross_box_email = cross_thread.get("box_email")
            print(f"🔍 [THREAD] Cross-mailbox thread ({cross_box_email}) has history: {cross_history}")
            
            # Cerca un thread locale che sia collegato alla conversazione con scoring migliorato
            local_response = self.supabase.table("threads").select("*").eq("box_email", box_email).execute()
            
            best_match = None
            best_score = 0
            
            for local_thread in local_response.data:
                local_history = local_thread.get("history", [])
                local_subject = local_thread.get("subject", "")
                local_sender = local_thread.get("sender_email", "")
                
                # Calcola score basato su più fattori
                score = 0
                
                # 1. Sovrapposizione history (peso maggiore)
                overlap_count = len(set(local_history) & set(cross_history))
                score += overlap_count * 10
                
                # 2. Subject similarity (peso minore)
                if subject and local_subject:
                    if self._subjects_similar(subject, local_subject):
                        score += 5
                
                # 3. Sender match (peso minore)
                if sender_email and sender_email == local_sender:
                    score += 3
                
                # 4. Penalizza thread con poca sovrapposizione relativa
                if overlap_count > 0 and len(local_history) > 0:
                    overlap_ratio = overlap_count / len(local_history)
                    if overlap_ratio < 0.3:  # Meno del 30% di sovrapposizione
                        score -= 2
                
                print(f"� [THREAD] Thread {local_thread.get('thread_id')}: overlap={overlap_count}/{len(local_history)}, subject_match={self._subjects_similar(subject, local_subject) if subject and local_subject else False}, score={score}")
                
                if score > best_score:
                    best_score = score
                    best_match = local_thread
            
            # Controlla se abbiamo un match abbastanza buono
            if best_match and best_score >= 8:  # Soglia minima per considerare un match valido
                print(f"🎯 [THREAD] Best match found: {best_match.get('thread_id')} with score {best_score}")
                return {"thread": best_match, "newly_created": False}
            elif best_match:
                print(f"🚫 [THREAD] Match found but score too low: {best_score} < 8 (thread: {best_match.get('thread_id')})")
            else:
                print(f"🚫 [THREAD] No matching local thread found")
            
            # Se non trova un thread locale collegato, crea un nuovo thread
            print(f"🆕 [THREAD] Creating new local thread for mailbox {box_email} connected to cross-mailbox conversation")
            
            new_thread = self.create_thread(
                started_at=message_timestamp,
                history=[reply_to_id, message_id],  # Include il reply_to_id per collegare la conversazione
                subject=subject,
                sender_email=sender_email,
                cc_emails=cc_emails or [],
                last_message_id=message_id,
                last_message_at=message_timestamp,
                has_attachments=False,  # Will be updated if attachments are processed
                category="CROSS_MAILBOX_REPLY",
                human_response=False,
                last_sender_email=sender_email,
                box_email=box_email
            )
            
            if new_thread and new_thread.get("thread_id"):
                print(f"✅ [THREAD] Created new local thread {new_thread.get('thread_id')} for cross-mailbox conversation")
                return {"thread": new_thread, "newly_created": True}
            else:
                print(f"❌ [THREAD] Failed to create new local thread for {box_email}")
                return None
            
        except Exception as e:
            print(f"❌ Error finding/creating local thread: {e}")
            return None
    
    def _subjects_similar(self, subject1: str, subject2: str) -> bool:
        """
        Helper per confrontare subject simili (rimuove Re:, Fwd:, etc.)
        
        Args:
            subject1: First subject to compare
            subject2: Second subject to compare
            
        Returns:
            True if subjects are similar after normalization
        """
        import re
        
        # Normalizza i subject rimuovendo prefissi comuni
        clean1 = re.sub(r'^(Re:|Fwd:|RE:|FWD:|Fw:|\[EXTERNAL\]|\[Ext\])\s*', '', subject1 or '', re.IGNORECASE).strip()
        clean2 = re.sub(r'^(Re:|Fwd:|RE:|FWD:|Fw:|\[EXTERNAL\]|\[Ext\])\s*', '', subject2 or '', re.IGNORECASE).strip()
        
        # Confronta case-insensitive
        return clean1.lower() == clean2.lower() if clean1 and clean2 else False
    
    def save_attachment(self, attachment_data: dict) -> Optional[str]:
        """
        Save attachment metadata to the email_attachments table.
        
        Args:
            attachment_data: Dictionary containing attachment metadata with keys:
                - thread_id: UUID of the thread
                - message_id: ID of the email message
                - sender: Email address of the sender
                - receiver: Email address of the receiver
                - cc: Array of CC email addresses
                - filename: Original filename of the attachment
                - file_path: Full path where file is stored on server
                - mime_type: MIME type of the file
                - size: Size in bytes
                - file_hash: SHA-256 hash of the file
                - service_id: UUID of the subscription service
                
        Returns:
            attachment_id (UUID) of saved attachment or None if failed
        """
        try:
            # Map the attachment_data to the correct database fields
            db_data = {
                "message_id": attachment_data.get("message_id"),
                "sender": attachment_data.get("sender"),  # Email address of sender
                "receiver": attachment_data.get("receiver"),  # Email address of receiver
                "cc": attachment_data.get("cc", []),  # Array of CC addresses
                "file_name": attachment_data.get("filename"),  # Nome file con timestamp salvato su disco
                "file_path": attachment_data.get("file_path"),  # Full storage path
                "mime_type": attachment_data.get("mime_type"),
                "size_bytes": attachment_data.get("size"),
                "thread_id": attachment_data.get("thread_id"),
                "service_id": attachment_data.get("service_id"),
                "file_hash": attachment_data.get("file_hash")
            }
            
            # Remove None values to let database handle defaults
            db_data = {k: v for k, v in db_data.items() if v is not None}
            
            result = self.supabase.table("email_attachments").insert(db_data).execute()
            
            if result.data and len(result.data) > 0:
                attachment_id = result.data[0].get("attachment_id")
                filename = attachment_data.get("filename", "")
                print(f"✅ [DB] Saved attachment {filename} with ID {attachment_id}")
                return attachment_id
            else:
                print(f"❌ [DB] Failed to save attachment {attachment_data.get('filename')}")
                return None
                
        except Exception as e:
            print(f"❌ [DB] Error saving attachment {attachment_data.get('filename')}: {e}")
            return None
    
    def get_service_id_by_email(self, email: str) -> Optional[str]:
        """
        Get the service_id for a given email from subscription_services table.
        
        Args:
            email: Email address to lookup
            
        Returns:
            service_id (UUID) if found, None otherwise
        """
        try:
            response = self.supabase.table("subscription_services").select("service_id").eq("email", email.lower()).execute()
            
            if response.data and len(response.data) > 0:
                service_id = response.data[0].get("service_id")
                print(f"🔍 [DB] Found service_id {service_id} for email {email}")
                return service_id
            else:
                print(f"❌ [DB] No service_id found for email {email}")
                return None
                
        except Exception as e:
            print(f"❌ [DB] Error getting service_id for {email}: {e}")
            return None
    
    def attachment_exists_by_hash_and_message(self, file_hash: str, message_id: str) -> Optional[str]:
        """
        Check if an attachment with the same hash and message_id already exists.
        This helps with deduplication when the same email is processed by multiple mailboxes.
        
        Args:
            file_hash: SHA-256 hash of the file
            message_id: ID of the email message
            
        Returns:
            attachment_id (UUID) if found, None otherwise
        """
        try:
            response = self.supabase.table("email_attachments").select("attachment_id").eq("file_hash", file_hash).eq("message_id", message_id).execute()
            
            if response.data and len(response.data) > 0:
                attachment_id = response.data[0].get("attachment_id")
                print(f"🔍 [DB] Found existing attachment with hash {file_hash[:16]}... and message_id {message_id}")
                return attachment_id
            else:
                return None
                
        except Exception as e:
            print(f"❌ [DB] Error checking attachment existence: {e}")
            return None
    
    def attachment_exists_in_thread_by_hash(self, thread_id: str, file_hash: str) -> Optional[str]:
        """
        Check if an attachment with the same hash already exists in this thread.
        This prevents duplicate attachments within the same conversation.
        
        Args:
            thread_id: ID of the thread to check
            file_hash: SHA-256 hash of the file
            
        Returns:
            attachment_id (UUID) if found, None otherwise
        """
        try:
            response = self.supabase.table("email_attachments").select("attachment_id").eq("thread_id", thread_id).eq("file_hash", file_hash).execute()
            
            if response.data and len(response.data) > 0:
                attachment_id = response.data[0].get("attachment_id")
                print(f"🔄 [DB] Found duplicate attachment in thread {thread_id} with hash {file_hash[:16]}...")
                return attachment_id
            else:
                return None
                
        except Exception as e:
            print(f"❌ [DB] Error checking thread attachment existence: {e}")
            return None
    
    def get_thread_attachments(self, thread_id: int) -> List[Dict]:
        """
        Get all attachments for a specific thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            List of attachment records
        """
        try:
            response = self.supabase.table("email_attachments").select("*").eq("thread_id", thread_id).order("created_at", desc=False).execute()
            
            if response.data:
                print(f"📎 [DB] Found {len(response.data)} attachments for thread {thread_id}")
                return response.data
            else:
                return []
                
        except Exception as e:
            print(f"❌ [DB] Error getting thread attachments: {e}")
            return []
    
    def get_attachment_by_id(self, attachment_id: str) -> Optional[Dict]:
        """
        Get attachment details by ID.
        
        Args:
            attachment_id: UUID of the attachment
            
        Returns:
            Attachment record if found, None otherwise
        """
        try:
            response = self.supabase.table("email_attachments").select("*").eq("attachment_id", attachment_id).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            else:
                return None
                
        except Exception as e:
            print(f"❌ [DB] Error getting attachment by ID: {e}")
            return None
    
    def update_thread_attachment_status(self, thread_id: str) -> bool:
        """
        Update has_attachments status based on actual attachments count.
        Call this after adding/removing attachments.
        
        Args:
            thread_id: ID of the thread to update
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Check if thread has any attachments
            response = self.supabase.table("email_attachments").select("attachment_id").eq("thread_id", thread_id).limit(1).execute()
            has_attachments = len(response.data) > 0
            
            # Update thread with the has_attachments flag
            update_response = self.supabase.table("threads").update({
                "has_attachments": has_attachments
            }).eq("thread_id", thread_id).execute()
            
            if update_response.data:
                print(f"📎 [THREAD] Updated has_attachments={has_attachments} for thread {thread_id}")
                return True
            else:
                print(f"❌ [THREAD] Failed to update has_attachments for thread {thread_id}")
                return False
                
        except Exception as e:
            print(f"❌ [THREAD] Error updating thread attachment status: {e}")
            return False
    
    def set_thread_has_attachments(self, thread_id: str, has_attachments: bool = True) -> bool:
        """
        Directly set the has_attachments flag for a thread.
        Use this when you know a thread has attachments without checking the database.
        
        Args:
            thread_id: ID of the thread to update
            has_attachments: Boolean flag to set
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            update_response = self.supabase.table("threads").update({
                "has_attachments": has_attachments
            }).eq("thread_id", thread_id).execute()
            
            if update_response.data:
                print(f"📎 [THREAD] Set has_attachments={has_attachments} for thread {thread_id}")
                return True
            else:
                print(f"❌ [THREAD] Failed to set has_attachments for thread {thread_id}")
                return False
                
        except Exception as e:
            print(f"❌ [THREAD] Error setting thread attachment flag: {e}")
            return False

    def update_extended_summary(self, thread_id: str, extended_summary: str) -> bool:
        """
        Update the extended_summary field for a thread.
        
        Args:
            thread_id: ID of the thread to update
            extended_summary: Extended summary text to set
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            response = self.supabase.table("threads").update({
                "extended_summary": extended_summary
            }).eq("thread_id", thread_id).execute()
            
            if response.data:
                print(f"📝 [THREAD] Updated extended_summary for thread {thread_id}")
                return True
            else:
                print(f"❌ [THREAD] Failed to update extended_summary for thread {thread_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating extended_summary: {e}")
            return False