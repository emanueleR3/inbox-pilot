from fastapi import APIRouter

router = APIRouter(tags=["chatbot"])

@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """
    Get chat history for a specific session
    """
    return {
        "messages": "Chat history - to be implemented"
    }
