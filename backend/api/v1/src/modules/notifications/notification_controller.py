from src.core.DAO.notification_dao import NotificationDAO
from src.handler_exception import (
    MissingFieldException,
    NotFoundException,
    DatabaseException
)


class NotificationController:
    def __init__(self):
        self.notification_dao = NotificationDAO()

    def get_notifications_by_email(self, email: str) -> dict:
        """
        Recupera tutte le notifiche per una specifica email.
        Include il body dell'email dalla tabella emails.
        
        Args:
            email: Email dell'utente
            
        Returns:
            dict con lista notifiche e conteggio
        """
        if not email:
            raise MissingFieldException(["email"])

        try:
            notifications = self.notification_dao.get_notifications_by_email(email)
            
            formatted_notifications = []
            for notif in notifications:
                formatted_notif = {
                    "notification_id": str(notif.notification_id),
                    "text": notif.text,
                    "type": notif.type,
                    "email": notif.email,
                    "email_id": str(notif.email_id) if notif.email_id else None,
                    "view": notif.view,
                }
                
                # Aggiungi i dati dell'email se disponibili
                if notif.email_data:
                    formatted_notif.update({
                        "email_body": notif.email_data.body,
                        "email_datetime": notif.email_data.datetime.isoformat() if notif.email_data.datetime else None,
                        "email_message_id": notif.email_data.message_id,
                        "email_outcome": notif.email_data.outcome,
                        "email_direction": notif.email_data.direction,
                        "email_has_attachment": notif.email_data.has_attachment
                    })
                else:
                    formatted_notif.update({
                        "email_body": None,
                        "email_datetime": None,
                        "email_message_id": None,
                        "email_outcome": None,
                        "email_direction": None,
                        "email_has_attachment": False
                    })
                
                formatted_notifications.append(formatted_notif)
            
            return {
                "notifications": formatted_notifications,
                "total": len(formatted_notifications)
            }
        except Exception as e:
            raise DatabaseException(operation=f"recupero notifiche: {str(e)}")

    def mark_notification_as_viewed(self, notification_id: str) -> dict:
        """
        Marca una notifica come vista.
        
        Args:
            notification_id: ID della notifica
            
        Returns:
            dict con conferma operazione
        """
        if not notification_id:
            raise MissingFieldException(["notification_id"])

        try:
            # Verifica che la notifica esista
            notification = self.notification_dao.get_notification_by_id(notification_id)
            if not notification:
                raise NotFoundException(detail=f"Notifica con ID {notification_id} non trovata")
            
            # Aggiorna lo stato
            updated = self.notification_dao.mark_notification_as_viewed(notification_id)
            
            return {
                "success": True,
                "message": "Notifica marcata come vista",
                "notification_id": notification_id,
                "view": True
            }
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"aggiornamento notifica: {str(e)}")
