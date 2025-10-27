from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, EmailStr, AnyUrl


class QuestionType(str, Enum):
    TEXT = "text"
    EMAIL = "email"
    URL = "url"
    PHONE = "phone"
    NUMBER = "number"
    DATE = "date"
    CHOICE_SINGLE = "choice_single"
    CHOICE_MULTI = "choice_multi"

class Option(BaseModel):
    id: str = Field(..., description="Unique id for the option")
    value: Optional[Any] = Field(None, description="Canonical value represented by the option")

class Question(BaseModel):
    id: str = Field(..., description="Unique identifier for the question")
    text: str = Field(..., description="Question text shown to the user")
    type: QuestionType = Field(..., description="Type of expected answer")
    options: Optional[List[Option]] = None
    helper_text: Optional[str] = None
    order: Optional[int] = None	
'''
    # conditional_on allows simple conditional flows: {question_id: expected_value}
    conditional_on: Optional[Dict[str, Any]] = None

    def is_applicable(self, answers: Dict[str, Any]) -> bool:
        # Return True if question should be asked given current answers (simple equality checks).
        if not self.conditional_on:
            return True
        for qid, expected in self.conditional_on.items():
            if qid not in answers:
                return False
            # simple match; for lists (multi choice) check membership
            val = answers[qid]
            if isinstance(val, list):
                if expected not in val:
                    return False
            else:
                if val != expected:
                    return False
        return True 
    '''

class Answer(BaseModel):
    question_id: str
    value: Any

class Quiz(BaseModel):
    id: Optional[str] = None
    questions: List[Question] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    def to_ordered_questions(self) -> List[Question]:
        return sorted(self.questions, key=lambda q: (q.order if q.order is not None else 1000, q.id))

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
    opening_hrs: Optional[str] = None
    employee_count: Optional[int] = None
    address: Optional[Address] = None
    products_services: Optional[str] = None
    tone_of_voice: Optional[str] = Field(default="professional", description="Preferred tone when replying to emails")
    email_address: Optional[EmailStr] = None
    email_signature: Optional[str] = None
    phone_number: Optional[str] = None
    vat_number: Optional[str] = None
    # metadata: Optional[Dict[str, Any]] = None

    def to_prompt_snippet(self) -> str:
        parts = []
        if self.company_name:
            parts.append(f"Company Name: {self.company_name}")
        if self.website:
            parts.append(f"Website: {self.website}")
        if self.industry:
            parts.append(f"Industry: {self.industry}")
        if self.employee_count:
            parts.append(f"Employee Count: {self.employee_count}")
        if self.address:
            addr_parts = [self.address.street, self.address.city, self.address.region, self.address.postal_code, self.address.country]
            addr_str = ", ".join(filter(None, addr_parts))
            if addr_str:
                parts.append(f"Address: {addr_str}")
        if self.products_services:
            parts.append(f"Products/Services: {self.products_services}")
        if self.tone_of_voice:
            parts.append(f"Tone of Voice: {self.tone_of_voice}")
        if self.email_signature:
            parts.append(f"Email Signature: {self.email_signature}")
        return "\n".join(parts)

__all__ = [
    "QuestionType",
    "Option",
    "Question",
    "Answer",
    "Quiz",
    "Address",
    "CompanyInfo",
]


