from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class QuizSessionBase(BaseModel):
    session_id: str = Field(..., description="ID univoco della sessione quiz")
    

class QuizSessionUpdate(BaseModel):
    final_markdown: Optional[str] = Field(None, description="Contenuto markdown finale del quiz")
    

class QuizSession(QuizSessionBase):
    final_markdown: Optional[str] = Field(None, description="Contenuto markdown finale del quiz")
    created_at: Optional[datetime] = Field(None, description="Data di creazione")
    updated_at: Optional[datetime] = Field(None, description="Data di ultimo aggiornamento")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "final_markdown": "# Quiz Completato\n\nScore: 80%",
                "created_at": "2025-12-21T10:00:00Z",
                "updated_at": "2025-12-21T10:30:00Z"
            }
        }