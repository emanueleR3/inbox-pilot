"""
Pydantic models for LLM responses and structured outputs.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional


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


class EmailClassificationResponse(BaseModel):
    """Response model for email classification (DEPRECATED - use EmailSummaryResponse + EmailCategoryResponse)."""
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
    mail_summary: str = Field(
        ..., 
        description="Riassunto della email corrente"
    )
    extended_summary: str = Field(
        ..., 
        description="Riassunto esteso e dettagliato dell'intera conversazione includendo questa email"
    )
    must_see_attachments: bool = Field(
        default=False,
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