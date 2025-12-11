"""Pydantic response models for LLM outputs."""

from pydantic import BaseModel, Field


class CleanedChunkResponse(BaseModel):
    """Structured response for cleaned text."""
    cleaned_text: str = Field(description="The cleaned text, without noise and with improved readability")
