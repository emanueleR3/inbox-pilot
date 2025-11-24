"""
Email HTML templates for different notification types.
"""

from typing import Optional
from datetime import datetime


def get_base_template(content: str, notification_type: str) -> str:
    """
    Base HTML template with consistent styling.
    
    Args:
        content: The main content HTML
        notification_type: Type of notification for color theming
    """
    # Color scheme based on notification type
    colors = {
        "HIGH_PRIORITY": {
            "primary": "#DC2626",  # Red
            "secondary": "#FEE2E2",
            "accent": "#991B1B"
        },
        "LOW_CONFIDENCE_CLASSIFICATION": {
            "primary": "#F59E0B",  # Amber
            "secondary": "#FEF3C7",
            "accent": "#D97706"
        },
        "EVENT_INVITE_RECEIVED": {
            "primary": "#3B82F6",  # Blue
            "secondary": "#DBEAFE",
            "accent": "#1D4ED8"
        },
        "APPOINTMENT_NOT_SCHEDULED": {
            "primary": "#8B5CF6",  # Purple
            "secondary": "#EDE9FE",
            "accent": "#6D28D9"
        },
        "EVENT_FOLLOWUP_RECEIVED": {
            "primary": "#3B82F6",  # Blue
            "secondary": "#DBEAFE",
            "accent": "#1D4ED8"
        },
        "INFORMATION_NOT_PRESENT": {
            "primary": "#F59E0B",  # Amber
            "secondary": "#FEF3C7",
            "accent": "#D97706"
        }
    }
    
    theme = colors.get(notification_type, colors["LOW_CONFIDENCE_CLASSIFICATION"])
    
    return f"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Notifica Corretto AI</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, {theme['primary']} 0%, {theme['accent']} 100%); padding: 40px 30px; border-radius: 12px 12px 0 0; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">
                                ✉️ Corretto AI
                            </h1>
                            <p style="margin: 10px 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 14px; font-weight: 500;">
                                Sistema di Gestione Email Intelligente
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            {content}
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 30px; background-color: #f9fafb; border-radius: 0 0 12px 12px; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0 0 10px 0; font-size: 14px; color: #6b7280;">
                                Questa è una notifica automatica dal tuo assistente email Corretto AI
                            </p>
                            <p style="margin: 0; font-size: 12px; color: #9ca3af;">
                                © {datetime.now().year} Corretto AI. Tutti i diritti riservati.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def create_high_priority_email(
    sender_email: str,
    subject: str,
    body: str,
    timestamp: str,
    summary_attachment: Optional[str] = None
) -> str:
    """Create HTML email for high priority notifications."""
    
    attachment_html = ""
    if summary_attachment:
        attachment_html = f"""
        <div style="margin-top: 20px; padding: 15px; background-color: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 6px;">
            <p style="margin: 0 0 5px 0; font-size: 13px; font-weight: 600; color: #92400e;">
                📎 Allegato
            </p>
            <p style="margin: 0; font-size: 13px; color: #78350f;">
                {summary_attachment}
            </p>
        </div>
        """
    
    content = f"""
    <div style="background-color: #fee2e2; border-left: 4px solid #dc2626; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
        <p style="margin: 0; font-size: 16px; font-weight: 700; color: #991b1b;">
            🚨 Email ad Alta Priorità Ricevuta
        </p>
    </div>
    
    <p style="margin: 0 0 20px 0; font-size: 15px; color: #374151; line-height: 1.6;">
        È stata ricevuta un'email classificata come <strong>alta priorità</strong> che richiede la tua attenzione immediata.
    </p>
    
    <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">DA</p>
                </td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827;">{sender_email}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">OGGETTO</p>
                </td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827; font-weight: 600;">{subject}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">DATA</p>
                </td>
                <td style="padding: 8px 0; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827;">{timestamp}</p>
                </td>
            </tr>
        </table>
    </div>
    
    <div style="background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <p style="margin: 0 0 10px 0; font-size: 13px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">
            Anteprima Messaggio
        </p>
        <p style="margin: 0; font-size: 14px; color: #374151; line-height: 1.8; white-space: pre-wrap;">
            {body[:500]}{'...' if len(body) > 500 else ''}
        </p>
    </div>
    
    {attachment_html}
    
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
        <p style="margin: 0; font-size: 13px; color: #6b7280; text-align: center;">
            💡 <em>Accedi alla tua casella email per visualizzare il messaggio completo e rispondere</em>
        </p>
    </div>
    """
    
    return get_base_template(content, "HIGH_PRIORITY")


def create_low_confidence_email(
    sender_email: str,
    subject: str,
    body: str,
    timestamp: str,
    summary_attachment: Optional[str] = None
) -> str:
    """Create HTML email for low confidence classification notifications."""
    
    attachment_html = ""
    if summary_attachment:
        attachment_html = f"""
        <div style="margin-top: 20px; padding: 15px; background-color: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 6px;">
            <p style="margin: 0 0 5px 0; font-size: 13px; font-weight: 600; color: #92400e;">
                📎 Allegato
            </p>
            <p style="margin: 0; font-size: 13px; color: #78350f;">
                {summary_attachment}
            </p>
        </div>
        """
    
    content = f"""
    <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
        <p style="margin: 0; font-size: 16px; font-weight: 700; color: #92400e;">
            ⚠️ Classificazione Incerta
        </p>
    </div>
    
    <p style="margin: 0 0 20px 0; font-size: 15px; color: #374151; line-height: 1.6;">
        Il sistema ha ricevuto un'email ma <strong>non è stato possibile classificarla con certezza</strong>. 
        È richiesta la tua revisione per determinare come procedere.
    </p>
    
    <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">DA</p>
                </td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827;">{sender_email}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">OGGETTO</p>
                </td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827; font-weight: 600;">{subject}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">DATA</p>
                </td>
                <td style="padding: 8px 0; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827;">{timestamp}</p>
                </td>
            </tr>
        </table>
    </div>
    
    <div style="background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <p style="margin: 0 0 10px 0; font-size: 13px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">
            Anteprima Messaggio
        </p>
        <p style="margin: 0; font-size: 14px; color: #374151; line-height: 1.8; white-space: pre-wrap;">
            {body[:500]}{'...' if len(body) > 500 else ''}
        </p>
    </div>
    
    {attachment_html}
    
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
        <p style="margin: 0; font-size: 13px; color: #6b7280; text-align: center;">
            💡 <em>Verifica manualmente questa email per confermare la classificazione corretta</em>
        </p>
    </div>
    """
    
    return get_base_template(content, "LOW_CONFIDENCE_CLASSIFICATION")


def create_event_invite_email(
    sender_email: str,
    subject: str,
    body: str,
    timestamp: str,
    summary_attachment: Optional[str] = None
) -> str:
    """Create HTML email for event invite notifications."""
    
    attachment_html = ""
    if summary_attachment:
        attachment_html = f"""
        <div style="margin-top: 20px; padding: 15px; background-color: #dbeafe; border-left: 4px solid #3b82f6; border-radius: 6px;">
            <p style="margin: 0 0 5px 0; font-size: 13px; font-weight: 600; color: #1e40af;">
                📎 Dettagli Evento
            </p>
            <p style="margin: 0; font-size: 13px; color: #1e3a8a;">
                {summary_attachment}
            </p>
        </div>
        """
    
    content = f"""
    <div style="background-color: #dbeafe; border-left: 4px solid #3b82f6; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
        <p style="margin: 0; font-size: 16px; font-weight: 700; color: #1e40af;">
            📅 Invito a Evento Ricevuto
        </p>
    </div>
    
    <p style="margin: 0 0 20px 0; font-size: 15px; color: #374151; line-height: 1.6;">
        Hai ricevuto un <strong>invito a un evento</strong>. Rivedi i dettagli e conferma la tua partecipazione.
    </p>
    
    <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">DA</p>
                </td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827;">{sender_email}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">OGGETTO</p>
                </td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827; font-weight: 600;">{subject}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">DATA</p>
                </td>
                <td style="padding: 8px 0; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827;">{timestamp}</p>
                </td>
            </tr>
        </table>
    </div>
    
    <div style="background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <p style="margin: 0 0 10px 0; font-size: 13px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">
            Dettagli Invito
        </p>
        <p style="margin: 0; font-size: 14px; color: #374151; line-height: 1.8; white-space: pre-wrap;">
            {body[:500]}{'...' if len(body) > 500 else ''}
        </p>
    </div>
    
    {attachment_html}
    
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
        <p style="margin: 0; font-size: 13px; color: #6b7280; text-align: center;">
            💡 <em>Accedi al tuo calendario per accettare o rifiutare l'invito</em>
        </p>
    </div>
    """
    
    return get_base_template(content, "EVENT_INVITE_RECEIVED")


def create_appointment_not_scheduled_email(
    sender_email: str,
    subject: str,
    body: str,
    timestamp: str,
    overlap: Optional[bool] = None,
    summary_attachment: Optional[str] = None
) -> str:
    """Create HTML email for appointment not scheduled notifications."""
    
    overlap_reason = ""
    if overlap is True:
        overlap_reason = """
        <div style="margin: 20px 0; padding: 15px; background-color: #fee2e2; border-left: 4px solid #dc2626; border-radius: 6px;">
            <p style="margin: 0 0 5px 0; font-size: 13px; font-weight: 600; color: #991b1b;">
                ⏰ Motivo
            </p>
            <p style="margin: 0; font-size: 13px; color: #7f1d1d;">
                Conflitto di orario: esiste già un appuntamento nello stesso slot temporale
            </p>
        </div>
        """
    elif overlap is False:
        overlap_reason = """
        <div style="margin: 20px 0; padding: 15px; background-color: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 6px;">
            <p style="margin: 0 0 5px 0; font-size: 13px; font-weight: 600; color: #92400e;">
                ℹ️ Motivo
            </p>
            <p style="margin: 0; font-size: 13px; color: #78350f;">
                L'appuntamento non è stato pianificato per altri motivi (es. informazioni incomplete)
            </p>
        </div>
        """
    
    attachment_html = ""
    if summary_attachment:
        attachment_html = f"""
        <div style="margin-top: 20px; padding: 15px; background-color: #ede9fe; border-left: 4px solid #8b5cf6; border-radius: 6px;">
            <p style="margin: 0 0 5px 0; font-size: 13px; font-weight: 600; color: #6d28d9;">
                📎 Dettagli
            </p>
            <p style="margin: 0; font-size: 13px; color: #5b21b6;">
                {summary_attachment}
            </p>
        </div>
        """
    
    content = f"""
    <div style="background-color: #ede9fe; border-left: 4px solid #8b5cf6; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
        <p style="margin: 0; font-size: 16px; font-weight: 700; color: #6d28d9;">
            🗓️ Appuntamento Non Pianificato
        </p>
    </div>
    
    <p style="margin: 0 0 20px 0; font-size: 15px; color: #374151; line-height: 1.6;">
        Il sistema ha ricevuto una <strong>richiesta di appuntamento</strong> ma non è stato possibile pianificarlo automaticamente. 
        È necessaria la tua revisione manuale.
    </p>
    
    {overlap_reason}
    
    <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">DA</p>
                </td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827;">{sender_email}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">OGGETTO</p>
                </td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827; font-weight: 600;">{subject}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">DATA</p>
                </td>
                <td style="padding: 8px 0; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827;">{timestamp}</p>
                </td>
            </tr>
        </table>
    </div>
    
    <div style="background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <p style="margin: 0 0 10px 0; font-size: 13px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">
            Richiesta Originale
        </p>
        <p style="margin: 0; font-size: 14px; color: #374151; line-height: 1.8; white-space: pre-wrap;">
            {body[:500]}{'...' if len(body) > 500 else ''}
        </p>
    </div>
    
    {attachment_html}
    
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
        <p style="margin: 0; font-size: 13px; color: #6b7280; text-align: center;">
            💡 <em>Rivedi la richiesta e pianifica manualmente l'appuntamento se necessario</em>
        </p>
    </div>
    """
    
    return get_base_template(content, "APPOINTMENT_NOT_SCHEDULED")

def create_event_followup_email(
    sender_email: str,
    subject: str,
    body: str,
    timestamp: str,
    summary_attachment: Optional[str] = None
) -> str:
    """Create HTML email for event follow-up notifications."""
    
    attachment_html = ""
    if summary_attachment:
        attachment_html = f"""
        <div style="margin-top: 20px; padding: 15px; background-color: #dbeafe; border-left: 4px solid #3b82f6; border-radius: 6px;">
            <p style="margin: 0 0 5px 0; font-size: 13px; font-weight: 600; color: #1e40af;">
                📎 Dettagli Follow-up
            </p>
            <p style="margin: 0; font-size: 13px; color: #1e3a8a;">
                {summary_attachment}
            </p>
        </div>
        """
    
    content = f"""
    <div style="background-color: #dbeafe; border-left: 4px solid #3b82f6; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
        <p style="margin: 0; font-size: 16px; font-weight: 700; color: #1e40af;">
            🔄 Follow-up Evento Ricevuto
        </p>
    </div>
    
    <p style="margin: 0 0 20px 0; font-size: 15px; color: #374151; line-height: 1.6;">
        Hai ricevuto un <strong>follow-up relativo a un evento</strong>. Rivedi i dettagli per ulteriori informazioni.
    </p>
    
    <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">DA</p>
                </td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827;">{sender_email}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">OGGETTO</p>
                </td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827; font-weight: 600;">{subject}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">DATA</p>
                </td>
                <td style="padding: 8px 0; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827;">{timestamp}</p>
                </td>
            </tr>
        </table>
    </div>
    <div style="background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <p style="margin: 0 0 10px 0; font-size: 13px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">
            Dettagli Follow-up
        </p>
        <p style="margin: 0; font-size: 14px; color: #374151; line-height: 1.8; white-space: pre-wrap;">
            {body[:500]}{'...' if len(body) > 500 else ''}
        </p>
    </div>
    {attachment_html}
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
        <p style="margin: 0; font-size: 13px; color: #6b7280; text-align: center;">
            💡 <em>Accedi al tuo calendario per rivedere i dettagli dell'evento</em>
        </p>
    </div>
    """
    return get_base_template(content, "EVENT_FOLLOWUP_RECEIVED")


def create_information_not_present_email(
    sender_email: str,
    subject: str,
    body: str,
    timestamp: str,
    summary_attachment: Optional[str] = None
) -> str:
    """Create HTML email for information not present notifications."""
    
    attachment_html = ""
    if summary_attachment:
        attachment_html = f"""
        <div style="margin-top: 20px; padding: 15px; background-color: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 6px;">
            <p style="margin: 0 0 5px 0; font-size: 13px; font-weight: 600; color: #92400e;">
                📎 Allegato
            </p>
            <p style="margin: 0; font-size: 13px; color: #78350f;">
                {summary_attachment}
            </p>
        </div>
        """
    
    content = f"""
    <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
        <p style="margin: 0; font-size: 16px; font-weight: 700; color: #92400e;">
            ℹ️ Informazioni Aziendali Non Disponibili
        </p>
    </div>
    
    <p style="margin: 0 0 20px 0; font-size: 15px; color: #374151; line-height: 1.6;">
        Il sistema ha ricevuto un'email che richiede una risposta, ma <strong>le informazioni aziendali necessarie non sono disponibili</strong> nel database. 
        È necessaria la tua revisione manuale per fornire una risposta appropriata.
    </p>
    
    <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">DA</p>
                </td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827;">{sender_email}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">OGGETTO</p>
                </td>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827; font-weight: 600;">{subject}</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; font-weight: 600;">DATA</p>
                </td>
                <td style="padding: 8px 0; text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #111827;">{timestamp}</p>
                </td>
            </tr>
        </table>
    </div>
    
    <div style="background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <p style="margin: 0 0 10px 0; font-size: 13px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">
            Anteprima Messaggio
        </p>
        <p style="margin: 0; font-size: 14px; color: #374151; line-height: 1.8; white-space: pre-wrap;">
            {body[:500]}{'...' if len(body) > 500 else ''}
        </p>
    </div>
    
    {attachment_html}
    
    <div style="background-color: #fef3c7; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <p style="margin: 0 0 10px 0; font-size: 13px; font-weight: 600; color: #92400e;">
            💡 Azione Richiesta
        </p>
        <p style="margin: 0; font-size: 14px; color: #78350f; line-height: 1.6;">
            Per abilitare le risposte automatiche future, aggiungi le informazioni aziendali nel database attraverso le impostazioni del servizio.
        </p>
    </div>
    
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
        <p style="margin: 0; font-size: 13px; color: #6b7280; text-align: center;">
            💡 <em>Rispondi manualmente a questa email e configura le informazioni aziendali per future automazioni</em>
        </p>
    </div>
    """
    
    return get_base_template(content, "INFORMATION_NOT_PRESENT")

def get_email_template(
    notification_type: str,
    sender_email: str,
    subject: str,
    body: str,
    timestamp: str,
    overlap: Optional[bool] = None,
    summary_attachment: Optional[str] = None
) -> str:
    """
    Get the appropriate email template based on notification type.
    
    Args:
        notification_type: Type of notification
        sender_email: Email address of the sender
        subject: Email subject
        body: Email body content
        timestamp: Timestamp string
        overlap: Whether appointment has overlap (for APPOINTMENT_NOT_SCHEDULED)
        summary_attachment: Summary of attachments if present
        
    Returns:
        HTML email template as string
    """
    if notification_type == "HIGH_PRIORITY":
        return create_high_priority_email(sender_email, subject, body, timestamp, summary_attachment)
    elif notification_type == "LOW_CONFIDENCE_CLASSIFICATION":
        return create_low_confidence_email(sender_email, subject, body, timestamp, summary_attachment)
    elif notification_type == "EVENT_INVITE_RECEIVED":
        return create_event_invite_email(sender_email, subject, body, timestamp, summary_attachment)
    elif notification_type == "APPOINTMENT_NOT_SCHEDULED":
        return create_appointment_not_scheduled_email(sender_email, subject, body, timestamp, overlap, summary_attachment)
    elif notification_type == "EVENT_FOLLOWUP_RECEIVED":
        return create_event_followup_email(sender_email, subject, body, timestamp, summary_attachment)
    elif notification_type == "INFORMATION_NOT_PRESENT":
        return create_information_not_present_email(sender_email, subject, body, timestamp, summary_attachment)
    else:
        # Fallback to low confidence template
        return create_low_confidence_email(sender_email, subject, body, timestamp, summary_attachment)
