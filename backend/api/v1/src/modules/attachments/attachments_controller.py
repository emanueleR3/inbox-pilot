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
            
            # Formatta gli attachments con info thread
            formatted_attachments = []
            for att in attachments:
                formatted_attachments.append(self._format_attachment_with_thread(att))
            
            return {
                "attachments": formatted_attachments,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            raise DatabaseException(operation=f"recupero attachments: {str(e)}")

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
