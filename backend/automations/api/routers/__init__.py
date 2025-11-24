from .jerry_router import router as chatbot_router
from .quiz_router import router as quiz_router
from .workflows_router import router as workflows_router

__all__ = ["chatbot_router", "quiz_router", "workflows_router"]
