import os
from src.core.DAO.attachments_dao import AttachmentsDAO
from src.handler_exception import (
    MissingFieldException,
    NotFoundException,
    DatabaseException,
    BadRequestException
)


class AttachmentsController:
    def __init__(self):
        self.attachments_dao = AttachmentsDAO()

    def get_attachments_by_service_id(
        self,
        service_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """
        Recupera la lista degli attachments per un service_id raggruppati per receiver.
        
        Returns:
            dict con lista attachments raggruppati per receiver, formati unici e info paginazione
        """
        if not service_id:
            raise MissingFieldException(["service_id"])

        try:
            result = self.attachments_dao.get_attachments_grouped_by_receiver(
                service_id=service_id,
                limit=limit,
                offset=offset
            )
            
            # Formatta ogni gruppo con le info thread
            formatted_groups = []
            for group in result["grouped_by_receiver"]:
                formatted_attachments = []
                for att in group["attachments"]:
                    formatted_attachments.append(self._format_attachment_with_thread(att))
                
                formatted_groups.append({
                    "receiver": group["receiver"],
                    "attachments": formatted_attachments,
                    "count": group["count"]
                })
            
            return {
                "grouped_by_receiver": formatted_groups,
                "unique_formats": result["unique_formats"],
                "total_receivers": result["total_receivers"],
                "total_attachments": result["total_attachments"],
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            raise DatabaseException(operation=f"recupero attachments raggruppati: {str(e)}")

    def _format_attachment_with_thread(self, attachment: dict) -> dict:
        """
        Formatta un attachment includendo le informazioni del thread.
        Se il thread non è disponibile, restituisce un placeholder.
        
        Args:
            attachment: dict con dati attachment e eventuale threads nested
            
        Returns:
            dict formattato con email_context
        """
        # Estrai info thread (può essere None se thread_id è null o non esiste)
        thread_info = attachment.get("threads")
        
        if thread_info:
            email_context = {
                "subject": thread_info.get("subject"),
                "sender_email": thread_info.get("sender_email"),
                "cc_emails": thread_info.get("cc_emails"),
                "summary": thread_info.get("summary"),
                "category": thread_info.get("category"),
                "subcategory": thread_info.get("subcategory"),
                "started_at": thread_info.get("started_at"),
                "last_message_at": thread_info.get("last_message_at"),
                "available": True
            }
        else:
            email_context = {
                "subject": "Informazioni non disponibili",
                "sender_email": None,
                "cc_emails": None,
                "summary": None,
                "category": None,
                "subcategory": None,
                "started_at": None,
                "last_message_at": None,
                "available": False
            }
        
        return {
            "attachment_id": attachment["attachment_id"],
            "thread_id": attachment.get("thread_id"),
            "email_id": attachment["email_id"],
            "sender": attachment["sender"],
            "receiver": attachment["receiver"],
            "cc": attachment.get("cc"),
            "file_name": attachment["file_name"],
            "mime_type": attachment["mime_type"],
            "size_bytes": attachment["size_bytes"],
            "created_at": attachment["created_at"],
            "service_id": attachment.get("service_id"),
            "email_context": email_context
        }

    def get_attachment_file(self, attachment_id: str) -> dict:
        """
        Recupera i dati necessari per servire il file.
        
        Returns:
            dict con file_path, file_name, mime_type per FileResponse
        """
        if not attachment_id:
            raise MissingFieldException(["attachment_id"])

        try:
            attachment = self.attachments_dao.get_attachment_by_id(attachment_id)
            if not attachment:
                raise NotFoundException(detail=f"Attachment con ID {attachment_id} non trovato")
            
            file_path = attachment.get("file_path")
            if not file_path:
                raise NotFoundException(detail="Percorso file non disponibile")
            
            # Verifica che il file esista sul server
            if not os.path.exists(file_path):
                raise NotFoundException(
                    detail=f"File non trovato sul server: {attachment['file_name']}"
                )
            
            return {
                "file_path": file_path,
                "file_name": attachment["file_name"],
                "mime_type": attachment["mime_type"]
            }
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"recupero file attachment: {str(e)}")

    def get_attachments_by_receiver(
        self,
        service_id: str,
        receiver: str,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """
        Recupera gli attachments per un receiver specifico.
        
        Args:
            service_id: ID del subscription service
            receiver: Email del receiver
            limit: Numero massimo di risultati
            offset: Offset per paginazione
            
        Returns:
            dict con attachments del receiver, formati unici e info paginazione
        """
        if not service_id:
            raise MissingFieldException(["service_id"])
        if not receiver:
            raise MissingFieldException(["receiver"])

        try:
            result = self.attachments_dao.get_attachments_by_receiver(
                service_id=service_id,
                receiver=receiver,
                limit=limit,
                offset=offset
            )
            
            # Formatta gli attachments con info thread
            formatted_attachments = []
            for att in result["attachments"]:
                formatted_attachments.append(self._format_attachment_with_thread(att))
            
            return {
                "receiver": receiver,
                "attachments": formatted_attachments,
                "unique_formats": result["unique_formats"],
                "total": result["total"],
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            raise DatabaseException(operation=f"recupero attachments per receiver: {str(e)}")
