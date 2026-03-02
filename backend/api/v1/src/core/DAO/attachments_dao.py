import logging
from typing import List, Optional, Dict
from collections import defaultdict
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
        Recupera gli attachments per un dato service_id con informazioni del thread.
        
        Args:
            service_id: ID del subscription service
            limit: Numero massimo di risultati
            offset: Offset per la paginazione
            
        Returns:
            Lista di attachment come dizionari con info thread annesse
        """
        try:
            response = (
                self.supabase.table("email_attachments")
                .select(
                    "attachment_id, thread_id, email_id, sender, file_name, "
                    "mime_type, size_bytes, created_at, service_id, receiver, cc, "
                    "threads(subject, sender_email, cc_emails, summary, category, subcategory, started_at, last_message_at)"
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
        Recupera un singolo attachment per ID con informazioni del thread.
        
        Args:
            attachment_id: ID dell'attachment
            
        Returns:
            Dict con i dati dell'attachment e info thread o None se non trovato
        """
        try:
            response = (
                self.supabase.table("email_attachments")
                .select(
                    "*, threads(subject, sender_email, cc_emails, summary, category, subcategory, started_at, last_message_at)"
                )
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

    def get_attachments_grouped_by_receiver(
        self,
        service_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """
        Recupera gli attachments per un service_id raggruppati per receiver.
        
        Args:
            service_id: ID del subscription service
            limit: Numero massimo di risultati
            offset: Offset per la paginazione
            
        Returns:
            Dict con attachments raggruppati per receiver e formati unici
        """
        try:
            # Recupera tutti gli attachments (senza limit per il raggruppamento completo)
            response = (
                self.supabase.table("email_attachments")
                .select(
                    "attachment_id, thread_id, email_id, sender, file_name, "
                    "mime_type, size_bytes, created_at, service_id, receiver, cc, "
                    "threads(subject, sender_email, cc_emails, summary, category, subcategory, started_at, last_message_at)"
                )
                .eq("service_id", service_id)
                .order("created_at", desc=True)
                .execute()
            )
            
            all_attachments = response.data or []
            
            # Raggruppa per receiver
            grouped = defaultdict(list)
            unique_formats = set()
            
            for att in all_attachments:
                receiver = att.get("receiver")
                grouped[receiver].append(att)
                mime_type = att.get("mime_type")
                if mime_type:
                    unique_formats.add(mime_type)
            
            # Converti in lista e applica paginazione
            receivers_list = []
            for receiver, attachments in sorted(grouped.items()):
                receivers_list.append({
                    "receiver": receiver,
                    "attachments": attachments,
                    "count": len(attachments)
                })
            
            # Applica paginazione sulla lista di receivers
            paginated_receivers = receivers_list[offset:offset + limit]
            
            return {
                "grouped_by_receiver": paginated_receivers,
                "unique_formats": sorted(list(unique_formats)),
                "total_receivers": len(receivers_list),
                "total_attachments": len(all_attachments)
            }
        except Exception as e:
            logging.exception(f"Errore nel recupero attachments raggruppati per service_id={service_id}: {e}")
            raise

    def get_attachments_by_receiver(
        self,
        service_id: str,
        receiver: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """
        Recupera gli attachments per un receiver specifico.
        
        Args:
            service_id: ID del subscription service
            receiver: Email del receiver
            limit: Numero massimo di risultati
            offset: Offset per la paginazione
            
        Returns:
            Dict con attachments del receiver e formati unici
        """
        try:
            # Recupera gli attachments per il receiver specifico
            response = (
                self.supabase.table("email_attachments")
                .select(
                    "attachment_id, thread_id, email_id, sender, file_name, "
                    "mime_type, size_bytes, created_at, service_id, receiver, cc, "
                    "threads(subject, sender_email, cc_emails, summary, category, subcategory, started_at, last_message_at)"
                )
                .eq("service_id", service_id)
                .eq("receiver", receiver)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            
            attachments = response.data or []
            
            # Estrai formati unici
            unique_formats = set()
            for att in attachments:
                mime_type = att.get("mime_type")
                if mime_type:
                    unique_formats.add(mime_type)
            
            # Conta totale per questo receiver
            count_response = (
                self.supabase.table("email_attachments")
                .select("attachment_id", count="exact")
                .eq("service_id", service_id)
                .eq("receiver", receiver)
                .execute()
            )
            
            return {
                "receiver": receiver,
                "attachments": attachments,
                "unique_formats": sorted(list(unique_formats)),
                "total": count_response.count or 0
            }
        except Exception as e:
            logging.exception(f"Errore nel recupero attachments per receiver={receiver}, service_id={service_id}: {e}")
            raise
