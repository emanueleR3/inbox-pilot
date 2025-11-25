"""
Pydantic models for LLM responses and structured outputs.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum


class LanguageDetectionResponse(BaseModel):
    """Response model for language detection."""
    language: Literal["ITA", "ENG"] = Field(
        ..., 
        description="Lingua del testo: ITA per Italiano, ENG per Inglese"
    )


class CategoryClassificationResponse(BaseModel):
    """Response model for email category classification."""
    category: str = Field(..., description="Detected email category")
    subcategory: str = Field(None, description="Detected email subcategory")
    confidence: float = Field(..., description="Confidence score 0.0-1.0")


class EmailFilterResponse(BaseModel):
    """Response model for email body filtering."""
    filtered_body: str = Field(
        ..., 
        description="Corpo email filtrato da elementi strutturali e HTML residuo"
    )


class GuardrailResponse(BaseModel):
    """Response model for email security guardrail."""
    permitted: bool = Field(
        ..., 
        description="Se true, l'email può essere processata in sicurezza"
    )
    message_error: Optional[str] = Field(
        None, 
        description="Motivazione per cui l'email non può essere processata"
    )
    attempted_scam: bool = Field(
        ..., 
        description="Se true, l'email è stata identificata come potenziale truffa"
    )


class EmailSummaryResponse(BaseModel):
    """Response model for email summarization."""
    mail_summary: str = Field(
        ..., 
        description="Riassunto della email corrente"
    )
    extended_summary: str = Field(
        ..., 
        description="Riassunto esteso e dettagliato dell'intera conversazione includendo questa email"
    )


class EmailCategoryResponse(BaseModel):
    """Response model for email category classification only."""
    category: Literal[
        "PROMOTION", 
        "SOCIAL_NOTIFICATION", 
        "INFO_PROVIDED", 
        "INFO_REQUESTED", 
        "CALENDAR_EVENT", 
        "TRANSACTIONAL", 
        "OTHER"
    ] = Field(..., description="Categoria della email")
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Punteggio di confidenza da 0.0 a 1.0 con precisione alla prima cifra decimale"
    )
    must_see_attachments: bool = Field(
        ...,
        description="True se gli allegati sono fondamentali per comprendere o rispondere alla email, False altrimenti"
    )


class LowConfidenceClassification(BaseModel):
    """Response model when classification confidence is too low."""
    message_id: str = Field(..., description="ID del messaggio email")
    thread_id: str = Field(..., description="ID del thread")
    status: Literal["low_confidence_classification"] = Field(
        default="low_confidence_classification",
        description="Stato del risultato"
    )
    message: str = Field(..., description="Messaggio di spiegazione")
    result: dict = Field(..., description="Risultato con classificazione a bassa confidence")


class DangerousEmailDetected(BaseModel):
    """Response model when dangerous email is detected."""
    message_id: str = Field(..., description="ID del messaggio email")
    thread_id: str = Field(..., description="ID del thread")
    status: Literal["dangerous_email"] = Field(
        default="dangerous_email",
        description="Stato del risultato"
    )
    message: str = Field(..., description="Messaggio di errore")
    attempted_scam: bool = Field(..., description="Se è stato rilevato un tentativo di scam")
    result: dict = Field(
        default={"extended_summary": None},
        description="Risultato vuoto per email pericolose"
    )


class AttachmentSummaryResponse(BaseModel):
    """Response model for attachment content summarization."""
    summary_attachments: str = Field(
        ..., 
        description="Riassunto discorsivo del contenuto di tutti gli allegati"
    )


class ReaderResponse(BaseModel):
    """Response model for Reader node analysis."""
    key_entities: dict = Field(
        ...,
        description="Entità chiave estratte dalla mail e allegati (date, informazioni, richieste, luoghi, ecc.)"
    )
    needs_response: bool = Field(
        ...,
        description="Se true, la mail richiede una risposta; se false, è conclusiva"
    )


class ReaderAppointmentResponse(BaseModel):
    """Response model for Reader node analysis of REQUEST_APPOINTMENT subcategory."""
    key_entities: dict = Field(
        ...,
        description="Entità chiave estratte dalla mail e allegati (date, informazioni, richieste, luoghi, ecc.)"
    )
    title_of_event: str = Field(
        ...,
        description="Titolo dell'appuntamento nella forma '[AI] APPUNTAMENTO + sender email'"
    )
    date: Optional[str] = Field(
        None,
        description="Data e ora dell'appuntamento in formato YYYY-MM-DDThh:mm:ss, None se non specificato"
    )
    duration: int = Field(
        60,
        description="Durata dell'appuntamento in minuti, default 60 se non specificato"
    )
    attendees: Optional[list] = Field(
        None,
        description="Lista di email degli invitati, None se non specificati"
    )
    place: Optional[str] = Field(
        None,
        description="Luogo dell'evento, None se non specificato"
    )
    additional_notes: Optional[str] = Field(
        None,
        description="Note aggiuntive sull'evento"
    )


class SchedulerResponse(BaseModel):
    """Response model for Scheduler node - appointment scheduling result."""
    scheduled: bool = Field(
        ...,
        description="True se l'appuntamento è stato prenotato con successo"
    )
    overlap: bool = Field(
        ...,
        description="True se c'è sovrapposizione con altri eventi"
    )
    event_code: Optional[str] = Field(
        None,
        description="Codice dell'evento prenotato, None se non prenotato"
    )
    proposed_slots: Optional[list] = Field(
        None,
        description="Array di date proposte in formato YYYY-MM-DD, None se non proposte"
    )


class ReaderAppointmentChangeResponse(BaseModel):
    """Response model for Reader node analysis of REQUEST_APPOINTMENT_CHANGE subcategory."""
    key_entities: dict = Field(
        ...,
        description="Entità chiave estratte dalla mail e allegati (date, informazioni, richieste, luoghi, ecc.)"
    )
    event_code: Optional[str] = Field(
        None,
        description="Codice alfanumerico a 6 cifre dell'evento da modificare, None se non trovato"
    )
    new_title_of_event: str = Field(
        ...,
        description="Nuovo titolo dell'appuntamento nella forma '[AI] APPUNTAMENTO + sender email'"
    )
    new_date: Optional[str] = Field(
        None,
        description="Nuova data e ora dell'appuntamento in formato YYYY-MM-DDThh:mm:ss, None se non specificato"
    )
    new_duration: Optional[int] = Field(
        None,
        description="Nuova durata dell'appuntamento in minuti, None se non specificato"
    )
    new_attendees: Optional[list] = Field(
        None,
        description="Nuovi invitati da aggiungere (array di email), None se non specificati"
    )
    new_place: Optional[str] = Field(
        None,
        description="Nuovo luogo dell'evento, None se non specificato"
    )
    additional_notes: Optional[str] = Field(
        None,
        description="Note aggiuntive sull'evento"
    )


class ReaderCancellationResponse(BaseModel):
    event_code: Optional[str] = Field(
        None,
        description="Codice alfanumerico a 6 cifre dell'evento da cancellare, None se non trovato"
    )
    """Response model for Reader node analysis of CANCEL_APPOINTMENT subcategory."""
    key_entities: dict = Field(
        ...,
        description="Entità chiave estratte dalla mail e allegati (date, informazioni, richieste, luoghi, ecc.)"
    )


# EVALUATOR SUBCATEGORY ENUMS
class PromotionSubcategory(str, Enum):
    """Subcategories for PROMOTION emails."""
    OFFER_PROMOTION = "OFFER_PROMOTION"
    NEWSLETTER = "NEWSLETTER"
    EVENT_INVITE = "EVENT_INVITE"
    PRODUCT_UPDATE = "PRODUCT_UPDATE"
    REQUEST_QUOTE = "REQUEST_QUOTE"


class SocialNotificationSubcategory(str, Enum):
    """Subcategories for SOCIAL_NOTIFICATION emails."""
    EVENT_INVITE = "EVENT_INVITE"
    PRODUCT_UPDATE = "PRODUCT_UPDATE"
    NEW_MESSAGE = "NEW_MESSAGE"
    CONNECTION_REQUEST = "CONNECTION_REQUEST"
    SYSTEM_ALERT = "SYSTEM_ALERT"
    SYSTEM_NOTIFICATION = "SYSTEM_NOTIFICATION"


class InfoProvidedSubcategory(str, Enum):
    """Subcategories for INFO_PROVIDED emails."""
    EVENT_INVITE = "EVENT_INVITE"
    PRODUCT_UPDATE = "PRODUCT_UPDATE"
    SENT_DOCUMENTS = "SENT_DOCUMENTS"
    PROVIDE_UPDATE = "PROVIDE_UPDATE"
    CONFIRM_APPOINTMENT = "CONFIRM_APPOINTMENT"
    FORWARD_INFO = "FORWARD_INFO"
    RESPONSE_TO_REQUEST = "RESPONSE_TO_REQUEST"
    REQUEST_DOCUMENT = "REQUEST_DOCUMENT"
    EVENT_FOLLOWUP = "EVENT_FOLLOWUP"
    INVOICE_OR_RECEIPT = "INVOICE_OR_RECEIPT"
    STATUS_NOTIFICATION = "STATUS_NOTIFICATION"
    TICKET_UPDATE = "TICKET_UPDATE"
    GENERAL_GREETING = "GENERAL_GREETING"


class InfoRequestedSubcategory(str, Enum):
    """Subcategories for INFO_REQUESTED emails."""
    CONNECTION_REQUEST = "CONNECTION_REQUEST"
    RESPONSE_TO_REQUEST = "RESPONSE_TO_REQUEST"
    REQUEST_DOCUMENT = "REQUEST_DOCUMENT"
    REQUEST_QUOTE = "REQUEST_QUOTE"
    REQUEST_APPOINTMENT = "REQUEST_APPOINTMENT"
    REQUEST_APPOINTMENT_CHANGE = "REQUEST_APPOINTMENT_CHANGE"
    REQUEST_STATUS_UPDATE = "REQUEST_STATUS_UPDATE"
    ASK_FOR_HELP = "ASK_FOR_HELP"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"
    PAYMENT_ISSUE = "PAYMENT_ISSUE"


class CalendarEventSubcategory(str, Enum):
    """Subcategories for CALENDAR_EVENT emails."""
    EVENT_INVITE = "EVENT_INVITE"
    CONFIRM_APPOINTMENT = "CONFIRM_APPOINTMENT"
    REQUEST_APPOINTMENT = "REQUEST_APPOINTMENT"
    REQUEST_APPOINTMENT_CHANGE = "REQUEST_APPOINTMENT_CHANGE"
    CANCEL_APPOINTMENT = "CANCEL_APPOINTMENT"
    EVENT_FOLLOWUP = "EVENT_FOLLOWUP"


class TransactionalSubcategory(str, Enum):
    """Subcategories for TRANSACTIONAL emails."""
    SYSTEM_ALERT = "SYSTEM_ALERT"
    SENT_DOCUMENTS = "SENT_DOCUMENTS"
    PROVIDE_UPDATE = "PROVIDE_UPDATE"
    REQUEST_STATUS_UPDATE = "REQUEST_STATUS_UPDATE"
    ASK_FOR_HELP = "ASK_FOR_HELP"
    ORDER_CONFIRMATION = "ORDER_CONFIRMATION"
    INVOICE_OR_RECEIPT = "INVOICE_OR_RECEIPT"
    PAYMENT_ISSUE = "PAYMENT_ISSUE"
    ACCOUNT_VERIFICATION = "ACCOUNT_VERIFICATION"
    STATUS_NOTIFICATION = "STATUS_NOTIFICATION"
    SYSTEM_NOTIFICATION = "SYSTEM_NOTIFICATION"
    TICKET_UPDATE = "TICKET_UPDATE"


class OtherSubcategory(str, Enum):
    """Subcategories for OTHER emails."""
    GENERAL_GREETING = "GENERAL_GREETING"
    INTERNAL_NOTE = "INTERNAL_NOTE"
    SPAM_OR_UNKNOWN = "SPAM_OR_UNKNOWN"
    UNRELATED_CONTENT = "UNRELATED_CONTENT"


# EVALUATOR RESPONSE MODELS FOR EACH CATEGORY
class PromotionEvaluatorResponse(BaseModel):
    """Response model for PROMOTION email evaluation."""
    priority_score: float = Field(
        ..., 
        ge=0.0, le=1.0,
        description="Punteggio di priorità da 0.0 a 1.0 (prima cifra decimale)"
    )
    subcategory: PromotionSubcategory = Field(
        ..., 
        description="Sottocategoria specifica per email promozionali"
    )


class SocialNotificationEvaluatorResponse(BaseModel):
    """Response model for SOCIAL_NOTIFICATION email evaluation."""
    priority_score: float = Field(
        ..., 
        ge=0.0, le=1.0,
        description="Punteggio di priorità da 0.0 a 1.0 (prima cifra decimale)"
    )
    subcategory: SocialNotificationSubcategory = Field(
        ..., 
        description="Sottocategoria specifica per notifiche social"
    )


class InfoProvidedEvaluatorResponse(BaseModel):
    """Response model for INFO_PROVIDED email evaluation."""
    priority_score: float = Field(
        ..., 
        ge=0.0, le=1.0,
        description="Punteggio di priorità da 0.0 a 1.0 (prima cifra decimale)"
    )
    subcategory: InfoProvidedSubcategory = Field(
        ..., 
        description="Sottocategoria specifica per informazioni fornite"
    )


class InfoRequestedEvaluatorResponse(BaseModel):
    """Response model for INFO_REQUESTED email evaluation."""
    priority_score: float = Field(
        ..., 
        ge=0.0, le=1.0,
        description="Punteggio di priorità da 0.0 a 1.0 (prima cifra decimale)"
    )
    subcategory: InfoRequestedSubcategory = Field(
        ..., 
        description="Sottocategoria specifica per richieste di informazioni"
    )


class CalendarEventEvaluatorResponse(BaseModel):
    """Response model for CALENDAR_EVENT email evaluation."""
    priority_score: float = Field(
        ..., 
        ge=0.0, le=1.0,
        description="Punteggio di priorità da 0.0 a 1.0 (prima cifra decimale)"
    )
    subcategory: CalendarEventSubcategory = Field(
        ..., 
        description="Sottocategoria specifica per eventi calendario"
    )


class TransactionalEvaluatorResponse(BaseModel):
    """Response model for TRANSACTIONAL email evaluation."""
    priority_score: float = Field(
        ..., 
        ge=0.0, le=1.0,
        description="Punteggio di priorità da 0.0 a 1.0 (prima cifra decimale)"
    )
    subcategory: TransactionalSubcategory = Field(
        ..., 
        description="Sottocategoria specifica per email transazionali"
    )


class OtherEvaluatorResponse(BaseModel):
    """Response model for OTHER category evaluation."""
    subcategory: OtherSubcategory = Field(..., description="Sottocategoria specifica")
    priority_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Punteggio di priorità della email (0.0-1.0)"
    )


class ExtractorCompanyInfoResponse(BaseModel):
    """Response model for company information extraction."""
    chunked_company_informations: dict = Field(
        ...,
        description="Dizionario contenente le informazioni aziendali rilevanti estratte per rispondere alla email"
    )
    """Response model for OTHER email evaluation."""
    priority_score: float = Field(
        ..., 
        ge=0.0, le=1.0,
        description="Punteggio di priorità da 0.0 a 1.0 (prima cifra decimale)"
    )
    subcategory: OtherSubcategory = Field(
        ..., 
        description="Sottocategoria specifica per email generiche"
    )