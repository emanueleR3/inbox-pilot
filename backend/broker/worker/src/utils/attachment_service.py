"""
Attachment service for downloading and managing email attachments.
Handles attachment download, storage, and database tracking for processed emails.
"""

import os
from dotenv import load_dotenv
import aiohttp
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Optional
from src.repositories.thread_repository import ThreadRepository
from src.utils.db_client import get_gmail_credentials, get_microsoft_credentials, get_imap_credentials, get_user_provider

load_dotenv()

class AttachmentService:
    """
    Service for handling email attachments download and storage.
    Supports Gmail API, Microsoft Graph API, and IMAP attachments.
    """
    
    def __init__(self):
        self.base_storage_path = os.getenv("ATTACHMENT_STORAGE_PATH", "/data/attachments")
        self.thread_repo = ThreadRepository()
        # Security settings
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.allowed_extensions = {
            '.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.gif', 
            '.zip', '.rar', '.xlsx', '.xls', '.ppt', '.pptx', '.csv'
        }
        # Blocked dangerous extensions
        self.blocked_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js', 
            '.jar', '.app', '.deb', '.pkg', '.dmg', '.iso', '.msi'
        }
    
    def _extract_email_address(self, email_field: str) -> str:
        """
        Extract email address from field that might contain name and email.
        Examples:
        - "Mario Rossi <mario@example.com>" -> "mario@example.com"
        - "mario@example.com" -> "mario@example.com" 
        - "<mario@example.com>" -> "mario@example.com"
        
        Args:
            email_field: Email field that might contain name and email
            
        Returns:
            Clean email address or original string if no email found
        """
        if not email_field:
            return ""
            
        # Cerca pattern <email@domain.com>
        angle_bracket_match = re.search(r'<([^>]+)>', email_field)
        if angle_bracket_match:
            return angle_bracket_match.group(1).strip()
        
        # Se non trova < >, cerca un pattern email diretto
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email_field)
        if email_match:
            return email_match.group(0).strip()
        
        # Se non trova nessun pattern email, ritorna la stringa originale
        return email_field.strip()
    
    async def process_attachments(self, email_data: dict, thread_id: int, email_id: str = None) -> List[Dict]:
        """
        Process attachments for an email that has been added to a thread.
        Downloads attachments and saves metadata to database.
        
        Args:
            email_data: Email data containing attachment metadata
            thread_id: Database thread ID where the email was added
            email_id: Database email ID for linking attachments (new required field)
            
        Returns:
            List of processed attachment info
        """
        attachments_metadata = email_data.get("attachments", [])
        if not attachments_metadata:
            print(f"📎 [ATTACHMENT] No attachments found for email {email_data.get('message_id')}")
            return []
        
        # Get email_id from parameter or from email_data
        if not email_id:
            email_id = email_data.get("email_id")
        
        if not email_id:
            print(f"❌ [ATTACHMENT] No email_id provided - cannot save attachments without email_id")
            return []
        
        processed_attachments = []
        provider = email_data.get("provider", "unknown")
        user_email = email_data.get("user_email") or email_data.get("from")
        email_date = email_data.get("date") or email_data.get("timestamp")
        
        # Se il provider non è specificato, prova a determinarlo dal database
        if provider == "unknown" and user_email:
            detected_provider = get_user_provider(user_email)
            if detected_provider:
                provider = detected_provider
                print(f"🔍 [ATTACHMENT] Auto-detected provider for {user_email}: {provider}")
        
        # Create storage directory structure: /data/attachments/[provider]/[email]/[date]/
        storage_dir = self._create_storage_directory(provider, user_email, email_date)
        
        print(f"📎 [ATTACHMENT] Processing {len(attachments_metadata)} attachments for thread {thread_id}")
        
        for attachment_meta in attachments_metadata:
            try:
                # Validate attachment before processing
                if not self._validate_attachment(attachment_meta):
                    print(f"🚫 [ATTACHMENT] Attachment validation failed: {attachment_meta.get('filename')}")
                    continue
                
                filename = attachment_meta.get('filename', 'unknown')
                
                # FASE 1: Prova a calcolare l'hash senza scaricare (per allegati IMAP che hanno già payload)
                potential_hash = None
                if provider == "imap" and "payload" in attachment_meta:
                    payload = attachment_meta["payload"]
                    if payload and isinstance(payload, bytes):
                        potential_hash = hashlib.sha256(payload).hexdigest()
                        print(f"🔍 [ATTACHMENT] Pre-calculated hash for {filename}: {potential_hash[:16]}...")
                
                # FASE 2: Controlla deduplicazione a livello di email
                if potential_hash:
                    existing_attachment_id = self.thread_repo.attachment_exists_by_hash_and_email(potential_hash, email_id)
                    if existing_attachment_id:
                        print(f"♻️ [ATTACHMENT] Skipping duplicate attachment {filename} for email {email_id}")
                        # Aggiungi comunque alle attachments processate con l'ID esistente
                        processed_attachments.append({
                            "attachment_id": existing_attachment_id,
                            "original_filename": filename,
                            "timestamped_filename": filename,  # Per i duplicati pre-download, usiamo il nome originale
                            "file_hash": potential_hash,
                            "size": attachment_meta.get("size", 0),
                            "duplicate": True
                        })
                        continue
                
                # FASE 2.5: Per provider senza payload, skip controllo by name/size (ora usiamo timestamp)
                # Con i timestamp, ogni file sarà automaticamente unico
                pass
                
                # FASE 3: Download e store attachment (se non è duplicato)
                stored_attachment = await self._download_and_store_attachment(
                    attachment_meta, email_data, storage_dir
                )
                
                if stored_attachment:
                    # FASE 4: Controlla deduplicazione dopo download (per provider che non hanno payload pre-calcolato)
                    file_hash = stored_attachment.get("file_hash")
                    if file_hash and not potential_hash:  # Solo se non abbiamo già controllato con payload
                        existing_attachment_id = self.thread_repo.attachment_exists_by_hash_and_email(file_hash, email_id)
                        if existing_attachment_id:
                            timestamped_filename = stored_attachment.get("timestamped_filename", filename)
                            print(f"🔄 [DB] Found duplicate attachment for email {email_id} with hash {file_hash[:16]}...")
                            print(f"♻️ [ATTACHMENT] Found duplicate after download {timestamped_filename} for email {email_id}")
                            # Rimuovi il file scaricato dato che è duplicato
                            try:
                                os.remove(stored_attachment["file_path"])
                                print(f"🗑️ [ATTACHMENT] Removed duplicate file: {stored_attachment['file_path']}")
                            except:
                                pass
                            
                            # Aggiungi alle attachments processate con l'ID esistente
                            processed_attachments.append({
                                "attachment_id": existing_attachment_id,
                                "original_filename": filename,
                                "timestamped_filename": timestamped_filename,
                                "file_hash": file_hash,
                                "size": stored_attachment.get("size", 0),
                                "duplicate": True
                            })
                            continue
                    
                    # FASE 5: Save to database (attachment nuovo)
                    db_attachment = await self._save_attachment_to_db(
                        stored_attachment, thread_id, email_data, email_id
                    )
                    
                    if db_attachment:
                        processed_attachments.append(db_attachment)
                        timestamped_filename = stored_attachment.get("timestamped_filename", filename)
                        print(f"✅ [ATTACHMENT] Processed new attachment: {timestamped_filename}")
                    else:
                        print(f"❌ [ATTACHMENT] Failed to save to DB: {filename}")
                else:
                    print(f"❌ [ATTACHMENT] Failed to download: {filename}")
                    
            except Exception as e:
                print(f"❌ [ATTACHMENT] Error processing {attachment_meta.get('filename')}: {e}")
                continue
        
        print(f"📎 [ATTACHMENT] Successfully processed {len(processed_attachments)}/{len(attachments_metadata)} attachments")
        
        # Update thread has_attachments flag if any attachments were processed
        if processed_attachments:
            try:
                self.thread_repo.set_thread_has_attachments(thread_id, True)
                print(f"📎 [ATTACHMENT] Updated has_attachments=True for thread {thread_id}")
            except Exception as e:
                print(f"❌ [ATTACHMENT] Failed to update has_attachments flag: {e}")
        
        return processed_attachments
    
    def _create_storage_directory(self, provider: str, user_email: str, email_date: str) -> str:
        """
        Create storage directory structure for attachments.
        
        Args:
            provider: Email provider (gmail, microsoft, imap)
            user_email: User's email address
            email_date: Email date/timestamp
            
        Returns:
            Full path to storage directory
        """
        # Sanitize email for directory name
        safe_email = user_email.replace("@", "_at_").replace(".", "_")
        
        # Extract date part for directory (YYYY-MM-DD)
        try:
            if email_date:
                if "T" in email_date:  # ISO format
                    date_part = email_date.split("T")[0]
                else:
                    # Try to parse other formats
                    date_part = datetime.now().strftime("%Y-%m-%d")
            else:
                date_part = datetime.now().strftime("%Y-%m-%d")
        except:
            date_part = datetime.now().strftime("%Y-%m-%d")
        
        # Create directory structure
        storage_dir = os.path.join(
            self.base_storage_path,
            provider,
            safe_email,
            date_part
        )
        
        os.makedirs(storage_dir, exist_ok=True)
        return storage_dir
    
    async def _download_and_store_attachment(
        self, attachment_meta: dict, email_data: dict, storage_dir: str
    ) -> Optional[Dict]:
        """
        Download attachment and store to filesystem with timestamp-based unique naming.
        
        Args:
            attachment_meta: Attachment metadata from listener
            email_data: Complete email data
            storage_dir: Directory to store the attachment
            
        Returns:
            Stored attachment info with timestamp-based filename, or None if failed
        """
        provider = email_data.get("provider")
        filename = attachment_meta.get("filename", "unknown_attachment")
        attachment_id = attachment_meta.get("attachment_id")
        
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        
        # Create timestamp-based unique filename: [nome_originale]_[timestamp]
        timestamp = int(datetime.now().timestamp() * 1000)  # Milliseconds for uniqueness
        name, ext = os.path.splitext(safe_filename)
        timestamped_filename = f"{name}_{timestamp}{ext}"
        file_path = os.path.join(storage_dir, timestamped_filename)
        
        print(f"� [ATTACHMENT] Timestamped filename: {safe_filename} → {timestamped_filename}")
        
        try:
            if provider == "gmail":
                success = await self._download_gmail_attachment(
                    attachment_meta, email_data, file_path
                )
            elif provider == "microsoft":
                success = await self._download_microsoft_attachment(
                    attachment_meta, email_data, file_path
                )
            elif provider == "imap":
                success = await self._download_imap_attachment(
                    attachment_meta, email_data, file_path
                )
            else:
                print(f"❌ [ATTACHMENT] Unsupported provider: {provider}")
                return None
            
            if success:
                # Verify file was actually created and has content
                if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                    print(f"❌ [ATTACHMENT] File not created or empty: {filename}")
                    return None
                
                # Calculate file hash for integrity
                file_hash = self._calculate_file_hash(file_path)
                file_size = os.path.getsize(file_path)
                
                # Verify file size matches expected (if provided)
                expected_size = attachment_meta.get("size", 0)
                if expected_size > 0 and abs(file_size - expected_size) > 1024:  # Allow 1KB difference
                    print(f"⚠️ [ATTACHMENT] File size mismatch for {filename}: expected {expected_size}, got {file_size}")
                
                print(f"✅ [ATTACHMENT] File downloaded successfully: {timestamped_filename} ({file_size} bytes)")
                
                return {
                    "original_filename": filename,         # Nome originale dall'email
                    "timestamped_filename": timestamped_filename, # Nome con timestamp salvato su disco
                    "file_path": file_path,
                    "size": file_size,
                    "mime_type": attachment_meta.get("mime_type", "application/octet-stream"),
                    "file_hash": file_hash,
                    "attachment_id": attachment_id
                }
            else:
                print(f"❌ [ATTACHMENT] Download failed for {filename}")
                return None
                
        except Exception as e:
            print(f"❌ [ATTACHMENT] Download error for {filename}: {e}")
            # Clean up partial file if it exists
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            return None
    
    async def _download_gmail_attachment(
        self, attachment_meta: dict, email_data: dict, file_path: str
    ) -> bool:
        """
        Download attachment from Gmail API.
        
        Args:
            attachment_meta: Attachment metadata
            email_data: Email data with auth tokens
            file_path: Where to save the file
            
        Returns:
            True if download successful
        """
        try:
            import base64
            
            # Get required data for Gmail API call
            attachment_id = attachment_meta.get("attachment_id")
            message_id = email_data.get("message_id")
            user_email = email_data.get("user_email")
            
            if not all([attachment_id, message_id, user_email]):
                print(f"❌ [ATTACHMENT] Missing required data for Gmail attachment download")
                return False
            
            # We need to get access token - this will require integration with auth system
            # For now, let's check if we have auth data in email_data
            access_token = email_data.get("access_token")
            if not access_token:
                # Try to get from auth system/database
                access_token = await self._get_gmail_access_token(user_email)
            
            if not access_token:
                print(f"❌ [ATTACHMENT] No access token available for Gmail user {user_email}")
                return False
            
            # Gmail API endpoint for attachment download
            url = f"https://gmail.googleapis.com/gmail/v1/users/{user_email}/messages/{message_id}/attachments/{attachment_id}"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Gmail returns base64url-encoded data
                        attachment_data = data.get("data", "")
                        if attachment_data:
                            # Decode base64url data
                            # Gmail uses base64url encoding (- and _ instead of + and /)
                            attachment_data = attachment_data.replace('-', '+').replace('_', '/')
                            # Add padding if necessary
                            while len(attachment_data) % 4:
                                attachment_data += '='
                            
                            decoded_data = base64.b64decode(attachment_data)
                            
                            # Write to file
                            with open(file_path, 'wb') as f:
                                f.write(decoded_data)
                            
                            print(f"✅ [ATTACHMENT] Gmail attachment saved: {attachment_meta.get('filename')}")
                            return True
                        else:
                            print(f"❌ [ATTACHMENT] No data in Gmail API response")
                            return False
                    
                    elif response.status == 401:
                        print(f"❌ [ATTACHMENT] Gmail API authentication failed for {user_email}")
                        return False
                    else:
                        error_text = await response.text()
                        print(f"❌ [ATTACHMENT] Gmail API error {response.status}: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"❌ [ATTACHMENT] Gmail download error for {attachment_meta.get('filename')}: {e}")
            return False
    
    async def _get_gmail_access_token(self, user_email: str) -> Optional[str]:
        """
        Get Gmail access token for user from auth system/database.
        
        Args:
            user_email: User's email address
            
        Returns:
            Access token or None if not available
        """
        try:
            # Recupera le credenziali dal database usando il db_client del broker
            credentials = get_gmail_credentials(user_email)
            access_token = credentials.get("access_token")
            
            if access_token:
                print(f"✅ [ATTACHMENT] Retrieved Gmail access token for {user_email}")
                return access_token
            else:
                print(f"❌ [ATTACHMENT] No Gmail access token found for {user_email}")
                return None
                
        except Exception as e:
            print(f"❌ [ATTACHMENT] Error getting Gmail token for {user_email}: {e}")
            return None
    
    async def _download_microsoft_attachment(
        self, attachment_meta: dict, email_data: dict, file_path: str
    ) -> bool:
        """
        Download attachment from Microsoft Graph API.
        
        Args:
            attachment_meta: Attachment metadata
            email_data: Email data with auth tokens
            file_path: Where to save the file
            
        Returns:
            True if download successful
        """
        try:
            import base64
            
            # Get required data for Microsoft Graph API call
            attachment_id = attachment_meta.get("attachment_id")
            # Usa microsoft_message_id se disponibile, altrimenti message_id
            message_id = email_data.get("microsoft_message_id") or email_data.get("message_id")
            user_email = email_data.get("user_email")
            
            print(f"📎 [ATTACHMENT] Microsoft download - attachment_id: {attachment_id}")
            print(f"📎 [ATTACHMENT] Microsoft download - message_id: {message_id}")
            print(f"📎 [ATTACHMENT] Microsoft download - user_email: {user_email}")
            
            if not all([attachment_id, message_id, user_email]):
                print(f"❌ [ATTACHMENT] Missing required data for Microsoft attachment download")
                return False
            
            # Get access token for Microsoft Graph
            access_token = email_data.get("access_token")
            if not access_token:
                access_token = await self._get_microsoft_access_token(user_email)
            
            if not access_token:
                print(f"❌ [ATTACHMENT] No access token available for Microsoft user {user_email}")
                return False
            
            # Microsoft Graph API endpoint for attachment download
            # Format: /users/{user}/messages/{message}/attachments/{attachment}/$value
            # URL encode the attachment_id to handle special characters
            from urllib.parse import quote
            encoded_attachment_id = quote(attachment_id, safe='')
            encoded_message_id = quote(message_id, safe='')
            encoded_user_email = quote(user_email, safe='@.')
            
            url = f"https://graph.microsoft.com/v1.0/users/{encoded_user_email}/messages/{encoded_message_id}/attachments/{encoded_attachment_id}/$value"
            
            print(f"📎 [ATTACHMENT] Microsoft Graph URL: {url}")
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/octet-stream"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        # Microsoft Graph returns raw attachment data
                        attachment_data = await response.read()
                        
                        if attachment_data:
                            # Write to file
                            with open(file_path, 'wb') as f:
                                f.write(attachment_data)
                            
                            print(f"✅ [ATTACHMENT] Microsoft attachment saved: {attachment_meta.get('filename')}")
                            return True
                        else:
                            print(f"❌ [ATTACHMENT] No data in Microsoft Graph API response")
                            return False
                    
                    elif response.status == 401:
                        print(f"❌ [ATTACHMENT] Microsoft Graph API authentication failed for {user_email}")
                        return False
                    elif response.status == 403:
                        print(f"❌ [ATTACHMENT] Microsoft Graph API access forbidden for {user_email}")
                        return False
                    elif response.status == 404:
                        print(f"❌ [ATTACHMENT] Microsoft attachment not found: {attachment_id}")
                        return False
                    else:
                        error_text = await response.text()
                        print(f"❌ [ATTACHMENT] Microsoft Graph API error {response.status}: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"❌ [ATTACHMENT] Microsoft download error for {attachment_meta.get('filename')}: {e}")
            return False
    
    async def _get_microsoft_access_token(self, user_email: str) -> Optional[str]:
        """
        Get Microsoft Graph access token for user from auth system/database.
        
        Args:
            user_email: User's email address
            
        Returns:
            Access token or None if not available
        """
        try:
            # Recupera le credenziali dal database usando il db_client del broker
            credentials = get_microsoft_credentials(user_email)
            access_token = credentials.get("access_token")
            
            if access_token:
                print(f"✅ [ATTACHMENT] Retrieved Microsoft access token for {user_email}")
                return access_token
            else:
                print(f"❌ [ATTACHMENT] No Microsoft access token found for {user_email}")
                return None
                
        except Exception as e:
            print(f"❌ [ATTACHMENT] Error getting Microsoft token for {user_email}: {e}")
            return None
    
    async def _download_imap_attachment(
        self, attachment_meta: dict, email_data: dict, file_path: str
    ) -> bool:
        """
        Download attachment from IMAP raw email data.
        
        Args:
            attachment_meta: Attachment metadata (può contenere payload o essere vuoto)
            email_data: Email data with raw email content
            file_path: Where to save the file
            
        Returns:
            True if download successful
        """
        try:
            import email
            import base64
            from email.header import decode_header
            
            # Se abbiamo già il payload nei metadati, usalo direttamente
            if "payload" in attachment_meta and attachment_meta["payload"]:
                attachment_data = attachment_meta["payload"]
                if isinstance(attachment_data, bytes):
                    # Write to file
                    with open(file_path, 'wb') as f:
                        f.write(attachment_data)
                    
                    print(f"✅ [ATTACHMENT] IMAP attachment saved from cached payload: {attachment_meta.get('filename')}")
                    return True
            
            # Altrimenti, cerca nell'email raw
            raw_email = email_data.get("raw")
            if not raw_email:
                print(f"❌ [ATTACHMENT] No raw email data for IMAP attachment")
                return False
            
            # Parse email message
            if isinstance(raw_email, bytes):
                msg = email.message_from_bytes(raw_email)
            else:
                msg = email.message_from_string(raw_email)
            
            # Find the attachment by filename or content type
            target_filename = attachment_meta.get("filename")
            target_content_type = attachment_meta.get("mime_type") or attachment_meta.get("content_type")
            
            # Walk through email parts to find the attachment
            for part in msg.walk():
                # Skip multipart containers
                if part.get_content_maintype() == 'multipart':
                    continue
                
                # Get filename from part
                part_filename = part.get_filename()
                part_content_type = part.get_content_type()
                
                if part_filename:
                    # Decode filename if necessary
                    try:
                        decoded_filename = decode_header(part_filename)[0]
                        if isinstance(decoded_filename[0], bytes):
                            part_filename = decoded_filename[0].decode(decoded_filename[1] or 'utf-8')
                        else:
                            part_filename = decoded_filename[0]
                    except:
                        pass
                
                # Check if this is our target attachment (by filename or content type)
                is_match = (
                    (target_filename and part_filename == target_filename) or
                    (target_content_type and part_content_type == target_content_type and 
                     part_content_type not in ["text/plain", "text/html"])
                )
                
                if is_match:
                    # Get attachment data
                    attachment_data = part.get_payload(decode=True)
                    
                    if attachment_data:
                        # Write to file
                        with open(file_path, 'wb') as f:
                            f.write(attachment_data)
                        
                        print(f"✅ [ATTACHMENT] IMAP attachment saved from email parsing: {target_filename or 'unnamed'}")
                        return True
                    else:
                        print(f"❌ [ATTACHMENT] Failed to decode IMAP attachment: {target_filename or 'unnamed'}")
                        return False
            
            print(f"❌ [ATTACHMENT] IMAP attachment not found in email: {target_filename or 'unnamed'}")
            return False
            
        except Exception as e:
            print(f"❌ [ATTACHMENT] IMAP download error for {attachment_meta.get('filename')}: {e}")
            return False
    
    async def _save_attachment_to_db(
        self, attachment_info: dict, thread_id: int, email_data: dict, email_id: str
    ) -> Optional[Dict]:
        """
        Save attachment metadata to database with deduplication check.
        Now uses email_id instead of message_id for linking.
        
        Args:
            attachment_info: Processed attachment info
            thread_id: Thread ID where email was added
            email_data: Original email data
            email_id: Database email ID for linking attachments
            
        Returns:
            Database attachment record or None if failed
        """
        try:
            # Extract sender and receiver information from email_data
            sender_email = email_data.get("from", "")
            receiver_email = email_data.get("to", "")
            cc_emails = email_data.get("cc", [])
            
            # Check if attachment already exists (deduplication)
            file_hash = attachment_info.get("file_hash")
            if file_hash and email_id:
                existing_attachment_id = self.thread_repo.attachment_exists_by_hash_and_email(file_hash, email_id)
                if existing_attachment_id:
                    print(f"❎ [ATTACHMENT] Attachment already exists with ID: {existing_attachment_id}")
                    return {
                        "attachment_id": existing_attachment_id,
                        "original_filename": attachment_info.get("original_filename", attachment_info.get("filename")),
                        "timestamped_filename": attachment_info.get("timestamped_filename", attachment_info.get("filename")),
                        "file_path": attachment_info["file_path"],
                        "size": attachment_info["size"],
                        "file_hash": file_hash,
                        "deduplication": True
                    }
            
            # Normalize email fields to ensure consistency and extract email addresses
            # Extract email from "Name <email>" format for sender
            sender = self._extract_email_address(sender_email)
            
            if isinstance(receiver_email, str):
                # If "to" is a single string, extract email and use as receiver
                receiver = self._extract_email_address(receiver_email)
            elif isinstance(receiver_email, list) and len(receiver_email) > 0:
                # If "to" is a list, take the first one as primary receiver
                receiver = self._extract_email_address(receiver_email[0])
                # Add the rest to CC if not already there
                additional_receivers = [self._extract_email_address(email) for email in receiver_email[1:]]
                if isinstance(cc_emails, list):
                    cc_emails.extend(additional_receivers)
                else:
                    cc_emails = additional_receivers
            else:
                receiver = ""
            
            # Normalize CC emails - extract email addresses from each CC entry
            if isinstance(cc_emails, list):
                cc_emails = [self._extract_email_address(email) for email in cc_emails if email]
            elif cc_emails:
                cc_emails = [self._extract_email_address(cc_emails)]
            else:
                cc_emails = []
            
            # Get service_id - we can use any of the involved emails, 
            # but let's prioritize the mailbox that's processing this (user_email)
            user_email = email_data.get("user_email") or receiver
            service_id = self.thread_repo.get_service_id_by_email(user_email)
            
            if not service_id:
                print(f"❌ [ATTACHMENT] No service_id found for email {user_email}")
                return None
            
            attachment_data = {
                "thread_id": thread_id,
                "email_id": email_id,  # Now using email_id instead of message_id
                "sender": sender,  # Normalized email address of sender
                "receiver": receiver,  # Normalized primary receiver email
                "cc": cc_emails,  # Array of normalized CC addresses
                "filename": attachment_info["timestamped_filename"],  # Nome file con timestamp salvato su disco
                "file_path": attachment_info["file_path"],  # Full storage path
                "mime_type": attachment_info["mime_type"],
                "size": attachment_info["size"],  # Size in bytes
                "file_hash": file_hash,
                "service_id": service_id
            }
            
            print(f"📎 [ATTACHMENT] Saving with email_id:{email_id}, sender:{sender}, receiver:{receiver}")
            
            # Save to database using thread repository
            attachment_id = self.thread_repo.save_attachment(attachment_data)
            
            if attachment_id:
                attachment_data["attachment_id"] = attachment_id
                return attachment_data
            else:
                return None
                
        except Exception as e:
            print(f"❌ [ATTACHMENT] Database save error: {e}")
            return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe filesystem storage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace problematic characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        sanitized = "".join(c if c in safe_chars else "_" for c in filename)
        
        # Ensure filename is not empty and not too long
        if not sanitized:
            sanitized = "attachment"
        
        if len(sanitized) > 200:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:190] + ext
        
        return sanitized
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of file for integrity checking.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA-256 hash as hex string
        """
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            print(f"❌ [ATTACHMENT] Hash calculation error: {e}")
            return ""
    
    def _validate_attachment(self, attachment_meta: dict) -> bool:
        """
        Validate attachment for security and size restrictions.
        
        Args:
            attachment_meta: Attachment metadata
            
        Returns:
            True if attachment is valid and safe to download
        """
        try:
            filename = attachment_meta.get("filename", "")
            size = attachment_meta.get("size", 0)
            mime_type = attachment_meta.get("mime_type", "")
            
            # Check if filename exists
            if not filename:
                print(f"🚫 [ATTACHMENT] No filename provided")
                return False
            
            # Check file size
            if size > self.max_file_size:
                print(f"🚫 [ATTACHMENT] File too large: {filename} ({size} bytes > {self.max_file_size} bytes)")
                return False
            
            # Check file extension
            file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ""
            
            # Block dangerous extensions
            if file_ext in self.blocked_extensions:
                print(f"🚫 [ATTACHMENT] Blocked file extension: {filename} ({file_ext})")
                return False
            
            # Check allowed extensions (if configured)
            if self.allowed_extensions and file_ext not in self.allowed_extensions:
                print(f"🚫 [ATTACHMENT] File extension not allowed: {filename} ({file_ext})")
                return False
            
            # Check for suspicious MIME types
            dangerous_mimes = [
                "application/x-executable",
                "application/x-msdownload",
                "application/x-msdos-program",
                "application/x-winexe"
            ]
            
            if mime_type in dangerous_mimes:
                print(f"🚫 [ATTACHMENT] Dangerous MIME type: {filename} ({mime_type})")
                return False
            
            # Check for double extensions (e.g., .txt.exe)
            if filename.count('.') > 1:
                all_extensions = filename.split('.')[1:]  # Skip the base name
                for ext in all_extensions[:-1]:  # Check all but the last extension
                    if ext.lower() in self.blocked_extensions:
                        print(f"🚫 [ATTACHMENT] Suspicious double extension: {filename}")
                        return False
            
            print(f"✅ [ATTACHMENT] Validation passed: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ [ATTACHMENT] Validation error for {attachment_meta.get('filename')}: {e}")
            return False