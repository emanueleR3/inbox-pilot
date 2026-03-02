import logging
from typing import List, Optional
from src.core.database import get_supabase_client
from src.core.model.notification import NotificationBase, NotificationWithEmail, EmailData


class NotificationDAO:
    def __init__(self):
        self.supabase = get_supabase_client()

    def get_notifications_by_email(self, email: str) -> List[NotificationWithEmail]:
        try:
            response = (
                self.supabase.table("notifications")
                .select(
                    "notification_id, text, type, email, email_id, view, "
                    "emails(body, datetime, message_id, outcome, direction, has_attachment)"
                )
                .eq("email", email)
                .eq("view", False)  
                .order("emails(datetime)", desc=True)
                .execute()
            )
            
            notifications = []
            for item in response.data or []:
                email_data = None
                if item.get("emails"):
                    email_data = EmailData(**item["emails"])
                
                notification = NotificationWithEmail(
                    notification_id=item["notification_id"],
                    text=item.get("text"),
                    type=item.get("type"),
                    email=item["email"],
                    email_id=item.get("email_id"),
                    view=item["view"],
                    email_data=email_data
                )
                notifications.append(notification)
            
            return notifications
        except Exception as e:
            logging.exception(f"Errore nel recupero notifiche per email={email}: {e}")
            raise

    def mark_notification_as_viewed(self, notification_id: str) -> Optional[NotificationBase]:
        try:
            response = (
                self.supabase.table("notifications")
                .update({"view": True})
                .eq("notification_id", notification_id)
                .execute()
            )
            
            if response.data:
                return NotificationBase(**response.data[0])
            return None
        except Exception as e:
            logging.exception(f"Errore nell'aggiornamento notifica con id={notification_id}: {e}")
            raise

    def get_notification_by_id(self, notification_id: str) -> Optional[NotificationBase]:
        try:
            response = (
                self.supabase.table("notifications")
                .select("*")
                .eq("notification_id", notification_id)
                .single()
                .execute()
            )
            
            if response.data:
                return NotificationBase(**response.data)
            return None
        except Exception as e:
            logging.exception(f"Errore nel recupero notifica con id={notification_id}: {e}")
            raise

