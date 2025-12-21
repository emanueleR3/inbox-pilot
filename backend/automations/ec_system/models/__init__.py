"""
Models package initialization.
"""

from .llm_responses import (
    CategoryClassificationResponse,
    EmailFilterResponse,
    GuardrailResponse,
    DangerousEmailDetected
)

__all__ = [
    "CategoryClassificationResponse",
    "EmailFilterResponse",
    "GuardrailResponse", 
    "DangerousEmailDetected"
]