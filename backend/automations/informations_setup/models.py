from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, EmailStr, AnyUrl

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
        if self.opening_hrs:
            lines.append(f"Opening Hours: {self.opening_hrs}")
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