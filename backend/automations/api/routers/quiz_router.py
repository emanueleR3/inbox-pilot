from typing import Optional
from fastapi import APIRouter, Query
from api.controllers.quiz_controller_v2 import QuizControllerV2

router = APIRouter(tags=["internal-quiz"], include_in_schema=False)
controller = QuizControllerV2()


@router.post("/start")
async def start_quiz(req: dict):
    """
    Start a new quiz session.
    
    Checks if the user has a qdrant collection (did scraping).
    If no collection exists, starts with the initial business question.

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
    
    When user confirms save (e.g., "ok, salva"), the save pipeline
    starts in background and response includes save_started=true.
    """
    session_id = req.get("session_id")
    answer = req.get("answer") or req.get("value")  # Support both 'answer' and 'value' for backward compatibility
    
    return await controller.submit_answer(session_id, answer)


@router.get("/{email}/state")
async def get_state(email: str):
    """
    Get the current state of a quiz session.
    
    Returns the full state including messages history and bullet list.
    """
    return await controller.get_state(email)


@router.post("/finish")
async def finish_quiz(req: dict):
    """
    Force finish the quiz and generate final markdown.
    
    Use this to end the quiz early if the user wants to skip remaining questions.
    """
    session_id = req.get("session_id")
    return await controller.finish_quiz(session_id)


@router.post("/save")
async def save_context(req: dict):
    """
    Manually trigger the save pipeline for a quiz session.
    
    Use this endpoint to trigger save programmatically without relying
    on chat message interpretation. The pipeline runs in background.
    
    Payload:
    - session_id (required)
    
    Returns:
    - started: true/false
    - session_id: the session ID
    - email: the user email
    - error: error message if started=false
    """
    session_id = req.get("session_id")
    return await controller.save_context(session_id)


@router.get("/save-status")
async def get_save_status(
    session_id: Optional[str] = Query(None, description="Session ID"),
    email: Optional[str] = Query(None, description="User email")
):
    """
    Get the status of a save pipeline operation.
    
    Query params (at least one required):
    - session_id: The quiz session ID
    - email: User email
    
    Returns:
    - phase: Current phase (PENDING, FETCHING_DATA, READING_JSON, 
             UPDATING_JSON_WITH_LLM, SAVING_JSON, DELETING_OLD_COLLECTION,
             CHUNKING, EMBEDDING, UPLOADING_TO_QDRANT, UPDATING_DATABASE,
             COMPLETED, FAILED)
    - actual_step: Current step number (1-9)
    - total_steps: Total steps (9)
    - started_at: ISO timestamp when save started
    - completed_at: ISO timestamp when save completed (if done)
    - error: Error message if failed
    - details: Additional details about current phase
    - is_running: true if pipeline is running
    - is_completed: true if pipeline completed successfully
    - is_failed: true if pipeline failed
    """
    return controller.get_save_status(session_id=session_id, email=email)


@router.get("/sessions")
async def list_sessions():
    return controller.list_sessions()

@router.get("/sessions/{email}")
async def get_sessions(email: str):
    return controller.get_sessions(email)