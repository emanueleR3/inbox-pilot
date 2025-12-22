from fastapi import APIRouter
from api.controllers.quiz_controller_v2 import QuizControllerV2

router = APIRouter(tags=["internal-quiz"], include_in_schema=False)
controller = QuizControllerV2()


@router.post("/start")
async def start_quiz(req: dict):
    """
    Start a new quiz session.
    
    Checks if the user has a qdrant collection (did scraping).
    If no collection exists, starts with the initial business question.
    If collection exists, TODO: implement RAG-based flow.

    Payload:
    - email (required)
    """
    email = req.get("email")
    return await controller.start_quiz(email=email)


@router.post("/answer")
async def submit_answer(req: dict):
    """
    Submit an answer to the current question.
    
    Returns the updated bullet list and next question.
    When all items are completed (or max turns reached), 
    returns done=true with the extracted markdown.
    """
    session_id = req.get("session_id")
    answer = req.get("answer") or req.get("value")  # Support both 'answer' and 'value' for backward compatibility
    
    return await controller.submit_answer(session_id, answer)


@router.get("/{session_id}/state")
async def get_state(session_id: str):
    """
    Get the current state of a quiz session.
    
    Returns the full state including messages history and bullet list.
    """
    return await controller.get_state(session_id)


@router.post("/finish")
async def finish_quiz(req: dict):
    """
    Force finish the quiz and generate final markdown.
    
    Use this to end the quiz early if the user wants to skip remaining questions.
    """
    session_id = req.get("session_id")
    return await controller.finish_quiz(session_id)


@router.get("/sessions")
async def list_sessions():
    """
    List all active quiz sessions.
    """
    return controller.list_sessions()



