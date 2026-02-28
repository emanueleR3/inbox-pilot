from datetime import datetime
from typing import Dict, Any, List


def retrieve_documents(query: str) -> str:
    """Retrieve documents based on a query."""
    print(f"Retrieving documents for query '{query}'")
    return f"Documents retrieved for query '{query}'."


def format_attachments_response(db_result: Dict[str, Any], target_sender_email: str) -> str:
    """
    Format the database result into a user-friendly Markdown response.
    
    This function takes the result from get_attachments_by_sender_email and formats it
    into a Markdown string that can be displayed to the user with clickable download links.
    
    Args:
        db_result: Dictionary with 'status' and 'data' keys from the DB query
        target_sender_email: The email address that was searched for
        
    Returns:
        Formatted Markdown string with one of three possible responses:
        - "Non hai mai ricevuto mail da questo indirizzo email: {email}"
        - "Non ci sono documenti allegati dalle mail ricevute da: {email}"
        - Markdown bullet list with clickable download links
    """
    status = db_result.get("status", "no_emails")
    data = db_result.get("data", [])
    
    # CASO 1: No emails found from this sender
    if status == "no_emails":
        return f"Non hai mai ricevuto mail da questo indirizzo email: {target_sender_email}"
    
    # CASO 2: Emails found but no attachments
    if status == "no_attachments":
        return f"Non ci sono documenti allegati dalle mail ricevute da: {target_sender_email}"
    
    # CASO 3: Attachments found - build Markdown list
    if status == "success" and data:
        lines = [f"📎 **Allegati ricevuti da {target_sender_email}:**\n"]
        
        for attachment in data:
            attachment_id = attachment.get("attachment_id", "")
            file_name = attachment.get("file_name", "File sconosciuto")
            created_at = attachment.get("created_at", "")
            
            # Format date in DD/MM/YYYY format
            try:
                if created_at:
                    # Parse ISO format datetime
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    else:
                        dt = created_at
                    date_str = dt.strftime("%d/%m/%Y")
                else:
                    date_str = "Data sconosciuta"
            except Exception:
                date_str = "Data sconosciuta"
            
            # Build the download URL
            download_url = f"/api/v1/attachments/download/{attachment_id}"
            
            # Format as Markdown bullet point with clickable link
            lines.append(f"- **{date_str}**: [{file_name}]({download_url}) (Clicca per scaricare o visualizzare)")
        
        return "\n".join(lines)
    
    # Fallback for unexpected status
    return f"Non hai mai ricevuto mail da questo indirizzo email: {target_sender_email}"