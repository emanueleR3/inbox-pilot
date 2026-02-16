import logging
from typing import List, Optional, Dict
from src.core.database import get_supabase_client


class AttachmentsDAO:
    def __init__(self):
        self.supabase = get_supabase_client()

    def get_attachments_by_service_id(
        self, 
        service_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """
        Recupera gli attachments per un dato service_id.
        
        Args:
            service_id: ID del subscription service
            limit: Numero massimo di risultati
            offset: Offset per la paginazione
            
        Returns:
            Lista di attachment come dizionari (senza file_path per sicurezza)
        """
        try:
            response = (
                self.supabase.table("email_attachments")
                .select(
                    "attachment_id, thread_id, email_id, sender, file_name, "
                    "mime_type, size_bytes, created_at, service_id, receiver, cc"
                )
                .eq("service_id", service_id)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logging.exception(f"Errore nel recupero attachments per service_id={service_id}: {e}")
            raise

    def get_attachment_by_id(self, attachment_id: str) -> Optional[Dict]:
        """
        Recupera un singolo attachment per ID.
        
        Args:
            attachment_id: ID dell'attachment
            
        Returns:
            Dict con i dati dell'attachment o None se non trovato
        """
        try:
            response = (
                self.supabase.table("email_attachments")
                .select("*")
                .eq("attachment_id", attachment_id)
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logging.exception(f"Errore nel recupero attachment con id={attachment_id}: {e}")
            raise

    def get_attachments_count_by_service_id(self, service_id: str) -> int:
        """
        Conta il numero totale di attachments per un service_id.
        
        Args:
            service_id: ID del subscription service
            
        Returns:
            Numero totale di attachments
        """
        try:
            response = (
                self.supabase.table("email_attachments")
                .select("attachment_id", count="exact")
                .eq("service_id", service_id)
                .execute()
            )
            return response.count or 0
        except Exception as e:
            logging.exception(f"Errore nel conteggio attachments per service_id={service_id}: {e}")
            raise
