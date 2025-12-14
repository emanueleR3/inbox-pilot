"""
Quiz models for the quiz system.

Contains Pydantic models for quiz data structures, API responses,
and legacy models for backward compatibility.
"""
from __future__ import annotations

from typing import Any, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, EmailStr, AnyUrl


# ============================================================================
# Bullet List Models (for new quiz flow)
# ============================================================================

class BulletListItem(BaseModel):
    """Single item in the bullet list checklist."""
    name: str = Field(..., description="Name/title of the information category")
    completed: bool = Field(default=False, description="Whether this item has been completed")
    info: Optional[str] = Field(default=None, description="Information collected for this item")


class QuizStartResponse(BaseModel):
    """Response when starting the quiz."""
    session_id: str = Field(..., description="Unique session identifier")
    question: str = Field(..., description="The initial question to ask")
    bullet_list: List[BulletListItem] = Field(default_factory=list, description="Current bullet list status")
    phase: str = Field(..., description="Current quiz phase")
    turn_count: int = Field(default=1, description="Current turn number")
    max_turns: int = Field(default=20, description="Maximum turns allowed")


class QuizAnswerResponse(BaseModel):
    """Response after submitting an answer."""
    done: bool = Field(default=False, description="Whether the quiz is complete")
    question: Optional[str] = Field(default=None, description="Next question or final message")
    bullet_list: List[BulletListItem] = Field(default_factory=list, description="Updated bullet list status")
    phase: str = Field(..., description="Current quiz phase")
    turn_count: int = Field(..., description="Current turn number")
    max_turns: int = Field(..., description="Maximum turns allowed")
    extracted_markdown: Optional[str] = Field(default=None, description="Final markdown if quiz is done")


# ============================================================================
# Legacy Models (kept for backward compatibility)
# ============================================================================

class Address(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class CompanyInfo(BaseModel):
    company_name: Optional[str] = None
    website: Optional[AnyUrl] = None
    industry: Optional[str] = None
    business_hours: Optional[dict] = None
    employee_count: Optional[int] = None
    address: Optional[Address] = None
    products_services: Optional[str] = None
    tone_of_voice: Optional[str] = Field(default="professional", description="Preferred tone when replying to emails")
    email_address: Optional[EmailStr] = None
    email_signature: Optional[str] = None
    phone_number: Optional[str] = None
    vat_number: Optional[str] = None
    
    def to_prompt_snippet(self) -> str:
        """
        Convert company info to a readable string for display or use in prompts.
        """
        lines = []
        if self.company_name:
            lines.append(f"Company Name: {self.company_name}")
        if self.industry:
            lines.append(f"Industry: {self.industry}")
        if self.website:
            lines.append(f"Website: {self.website}")
        if self.email_address:
            lines.append(f"Email: {self.email_address}")
        if self.phone_number:
            lines.append(f"Phone: {self.phone_number}")
        if self.address:
            addr_parts = []
            if self.address.street:
                addr_parts.append(self.address.street)
            if self.address.city:
                addr_parts.append(self.address.city)
            if self.address.region:
                addr_parts.append(self.address.region)
            if self.address.postal_code:
                addr_parts.append(self.address.postal_code)
            if self.address.country:
                addr_parts.append(self.address.country)
            if addr_parts:
                lines.append(f"Address: {', '.join(addr_parts)}")
        if self.employee_count:
            lines.append(f"Employee Count: {self.employee_count}")
        if self.business_hours:
            lines.append(f"Business Hours: {self.business_hours}")
        if self.products_services:
            lines.append(f"Products/Services: {self.products_services}")
        if self.tone_of_voice:
            lines.append(f"Tone of Voice: {self.tone_of_voice}")
        if self.vat_number:
            lines.append(f"VAT Number: {self.vat_number}")
        if self.email_signature:
            lines.append(f"Email Signature: {self.email_signature}")
        
        return "\n".join(lines) if lines else "No company information collected yet."


class Question(BaseModel):
    id: str = Field(..., description="Unique identifier for the question")
    text: str = Field(..., description="Question text shown to the user")
    helper_text: Optional[str] = None
    order: Optional[int] = None


class Answer(BaseModel):
    question_id: str
    value: Any


class Quiz(BaseModel):
    id: Optional[str] = None
    questions: List[Question] = Field(default_factory=list)
    answers: Optional[List[Answer]] = None
    created_at: datetime = Field(default_factory=datetime.now)


__all__ = [
    # New quiz flow models
    "BulletListItem",
    "QuizStartResponse",
    "QuizAnswerResponse",
    # Legacy models
    "Address",
    "CompanyInfo",
    "Question",
    "Answer",
    "Quiz",
]
