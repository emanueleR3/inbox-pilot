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
        Recupera la lista degli attachments per un service_id.
        
        Returns:
            dict con lista attachments e info paginazione
        """
        if not service_id:
            raise MissingFieldException(["service_id"])

        try:
            attachments = self.attachments_dao.get_attachments_by_service_id(
                service_id=service_id,
                limit=limit,
                offset=offset
            )
            total_count = self.attachments_dao.get_attachments_count_by_service_id(service_id)
            
            return {
                "attachments": attachments,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            raise DatabaseException(operation=f"recupero attachments: {str(e)}")

    def get_attachment_for_preview(self, attachment_id: str) -> dict:
        """
        Recupera i metadati di un attachment per il preview/visualizzazione.
        
        Returns:
            dict con metadati (senza file_path per sicurezza)
        """
        if not attachment_id:
            raise MissingFieldException(["attachment_id"])

        try:
            attachment = self.attachments_dao.get_attachment_by_id(attachment_id)
            if not attachment:
                raise NotFoundException(detail=f"Attachment con ID {attachment_id} non trovato")
            
            # Restituisce solo i metadati senza file_path
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
                "service_id": attachment.get("service_id")
            }
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"recupero attachment per preview: {str(e)}")

    def get_attachment_for_download(self, attachment_id: str) -> dict:
        """
        Recupera i metadati di un attachment per il download.
        Alias di get_attachment_for_preview, ma semanticamente distinto.
        
        Returns:
            dict con metadati (senza file_path per sicurezza)
        """
        return self.get_attachment_for_preview(attachment_id)
