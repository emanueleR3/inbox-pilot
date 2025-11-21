"""
Database client for Supabase operations.
Handles queries for retrieving user information for notifications.
"""

import os
import logging
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

class DatabaseClient:
    """Client for Supabase database operations."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("✅ Supabase client initialized successfully")
    
    def get_user_email_from_box_email(self, box_email: str) -> Optional[str]:
        """
        Retrieve user email from box_email through the following chain:
        box_email (subscription_services) -> subscription_id (subscriptions) 
        -> user_id (users_has_subscriptions) -> email (auth.users)
        
        Args:
            box_email: The email address from subscription_services table
            
        Returns:
            User email if found, None otherwise
        """
        try:
            logger.info(f"🔍 Looking up user email for box_email: {box_email}")
            
            # Step 1: Get subscription_id from subscription_services using box_email
            service_response = self.client.table("subscription_services") \
                .select("subscription_id") \
                .eq("email", box_email) \
                .limit(1) \
                .execute()
            
            if not service_response.data or len(service_response.data) == 0:
                logger.warning(f"⚠️ No subscription_service found for box_email: {box_email}")
                return None
            
            subscription_id = service_response.data[0].get("subscription_id")
            if not subscription_id:
                logger.warning(f"⚠️ No subscription_id found for box_email: {box_email}")
                return None
            
            logger.info(f"📋 Found subscription_id: {subscription_id}")
            
            # Step 2: Get user_id from users_has_subscriptions using subscription_id
            user_sub_response = self.client.table("users_has_subscriptions") \
                .select("user_id") \
                .eq("subscription_id", subscription_id) \
                .limit(1) \
                .execute()
            
            if not user_sub_response.data or len(user_sub_response.data) == 0:
                logger.warning(f"⚠️ No user found for subscription_id: {subscription_id}")
                return None
            
            user_id = user_sub_response.data[0].get("user_id")
            if not user_id:
                logger.warning(f"⚠️ No user_id found for subscription_id: {subscription_id}")
                return None
            
            logger.info(f"👤 Found user_id: {user_id}")
            
            # Step 3: Get email from auth.users using user_id
            # Use Supabase Admin API to access auth.users table
            user_response = self.client.auth.admin.get_user_by_id(user_id)
            
            if not user_response or not user_response.user:
                logger.warning(f"⚠️ No auth user found for user_id: {user_id}")
                return None
            
            user_email = user_response.user.email
            
            if user_email:
                logger.info(f"✅ Successfully retrieved user email: {user_email}")
                return user_email
            else:
                logger.warning(f"⚠️ User {user_id} exists but has no email")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error retrieving user email for box_email {box_email}: {str(e)}", exc_info=True)
            return None


# Global database client instance
_db_client: Optional[DatabaseClient] = None


def get_db_client() -> DatabaseClient:
    """
    Get or create the global database client instance.
    
    Returns:
        DatabaseClient instance
    """
    global _db_client
    
    if _db_client is None:
        _db_client = DatabaseClient()
    
    return _db_client


def get_user_email_from_box_email(box_email: str) -> Optional[str]:
    """
    Convenience function to get user email from box_email.
    
    Args:
        box_email: The box email address
        
    Returns:
        User email if found, None otherwise
    """
    client = get_db_client()
    return client.get_user_email_from_box_email(box_email)
