"""
Prompts for the QuizChain system.
Centralized prompt management for better maintainability and flexibility.
"""

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from models import Question


# Additional Pydantic models for LLM outputs
class QuizComplete(BaseModel):
    """Model indicating quiz completion."""
    done: bool = Field(description="Whether the quiz is complete")

class ExtractedCompanyInfo(BaseModel):
    """Model for extracted company information (flat structure for LLM output)."""
    company_name: Optional[str] = Field(default=None, description="Company name")
    website: Optional[str] = Field(default=None, description="Company website URL")
    industry: Optional[str] = Field(default=None, description="Industry sector")
    opening_hrs: Optional[str] = Field(default=None, description="Business opening hours")
    employee_count: Optional[int] = Field(default=None, description="Number of employees")
    address_street: Optional[str] = Field(default=None, description="Street address")
    address_city: Optional[str] = Field(default=None, description="City")
    address_region: Optional[str] = Field(default=None, description="Region or state")
    address_postal_code: Optional[str] = Field(default=None, description="Postal/ZIP code")
    address_country: Optional[str] = Field(default=None, description="Country")
    products_services: Optional[str] = Field(default=None, description="Products or services offered")
    tone_of_voice: Optional[str] = Field(default=None, description="Preferred communication tone")
    email_address: Optional[str] = Field(default=None, description="Company email address")
    email_signature: Optional[str] = Field(default=None, description="Email signature")
    phone_number: Optional[str] = Field(default=None, description="Contact phone number")
    vat_number: Optional[str] = Field(default=None, description="VAT/Tax number")


class Prompts:
    """
    Collection of prompts used in the quiz system.
    Uses PydanticOutputParser for automatic format instruction generation.
    """
    
    # Create parsers - using Question model from models.py
    question_parser = PydanticOutputParser(pydantic_object=Question)
    completion_parser = PydanticOutputParser(pydantic_object=QuizComplete)
    company_info_parser = PydanticOutputParser(pydantic_object=ExtractedCompanyInfo)
    
    @staticmethod
    def get_question_generator() -> ChatPromptTemplate:
        """
        Get the question generator prompt with format instructions.
        """
        return ChatPromptTemplate.from_messages([
            ("system", """Sei un esperto nella raccolta di informazioni aziendali tramite domande strutturate.
Il tuo obiettivo è raccogliere informazioni complete su un'azienda per costruirne il profilo, che servirà a costruire risposte ad email in ingresso all'azienda.

Genera la domanda successiva da porre in base a:
1. Le informazioni già raccolte
2. Campi comuni del profilo aziendale (nome, settore, sito web, indirizzo, prodotti/servizi, tono di voce, ecc.)
3. Flusso logico: poni domande di follow-up in base alle risposte precedenti

Numero di domande attuale: {current_count}/{max_questions}

Se abbiamo raggiunto {max_questions} domande o abbiamo informazioni sufficienti, restituisci un JSON con "done": true.
In caso contrario, genera la domanda successiva.

Domande e risposte precedenti:
{history}

{format_instructions}"""),
            ("user", "Genera la prossima domanda.")
        ]).partial(format_instructions=Prompts.question_parser.get_format_instructions())
    
    @staticmethod
    def get_company_info_extractor() -> ChatPromptTemplate:
        """
        Get the company info extraction prompt with format instructions.
        """
        return ChatPromptTemplate.from_messages([
            ("system", """Sei un esperto nell'estrazione di informazioni aziendali strutturate dai dati di Q&A.

Estrai tutte le informazioni aziendali disponibili dalle domande e risposte fornite.
Non inventare informazioni che non puoi ricavare. Poni a null per tutti i campi che non possono essere determinati dai dati.

{format_instructions}"""),
        ("user", """Domande e Risposte:
{qa_data}

Estrai le informazioni aziendali:""")
        ]).partial(format_instructions=Prompts.company_info_parser.get_format_instructions())


__all__ = ["Prompts", "QuizComplete", "ExtractedCompanyInfo"]
