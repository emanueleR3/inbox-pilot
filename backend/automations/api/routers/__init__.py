from .chatbot import router as chatbot_router
from .quiz import router as quiz_router
from .workflows import router as workflows_router

__all__ = ["chatbot_router", "quiz_router", "workflows_router"]
