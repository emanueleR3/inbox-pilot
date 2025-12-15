"""
Quiz Service V2 - Simplified State Machine Approach

This service manages quiz sessions using a simple state machine pattern
instead of LangGraph.
"""
import uuid
from typing import Optional, List

from quiz.flow.quiz_flow import QuizFlow
from quiz.flow.state import QuizState
from db_client import get_supabase_client


# In-memory session storage (consider Redis for production)
_sessions: dict[str, QuizFlow] = {}


def create_session(service_id: str) -> str:
    """
    Create a new quiz session for a service.
    
    Args:
        service_id: The ID of the subscription service
        
    Returns:
        The session ID
    """
    session_id = str(uuid.uuid4())
    _sessions[session_id] = QuizFlow(service_id=service_id, session_id=session_id)
    return session_id


def get_session(session_id: str) -> Optional[QuizFlow]:
    """
    Get an existing quiz session.
    
    Args:
        session_id: The session ID
        
    Returns:
        The QuizFlow instance or None if not found
    """
    return _sessions.get(session_id)


def delete_session(session_id: str) -> bool:
    """
    Delete a quiz session.
    
    Args:
        session_id: The session ID
        
    Returns:
        True if deleted, False if not found
    """
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


async def start_quiz(service_id: str, session_id: str) -> dict:
    """
    Start a new quiz for a service.
    
    Args:
        service_id: The ID of the subscription service
        session_id: The session ID
        
    Returns:
        The initial quiz response with question and bullet list
    """
    flow = get_session(session_id)
    if not flow:
        raise ValueError(f"Session not found: {session_id}")
    
    # Check if user has qdrant collection (did scraping)
    has_qdrant, qdrant_collection = await check_qdrant_collection(service_id)
    
    # Update flow with qdrant info
    flow.has_qdrant = has_qdrant
    flow.qdrant_collection = qdrant_collection
    
    # Start the quiz flow
    state = flow.start()
    
    # Persist informations_plan on start (especially important for Qdrant flow)
    current_plan: List[str] = [item.get("name") for item in state.get("bullet_list", []) if item.get("name")]
    if current_plan:
        await persist_informations_plan(state["service_id"], current_plan)
    
    # Build response
    return _build_response(state)


async def submit_answer(session_id: str, user_answer: str) -> dict:
    """
    Submit an answer to the current quiz question.
    
    Args:
        session_id: The session ID
        user_answer: The user's answer
        
    Returns:
        The next question or completion response
    """
    flow = get_session(session_id)
    if not flow:
        raise ValueError(f"Session not found: {session_id}")

    previous_state = flow.get_state()
    previous_plan: List[str] = []
    if previous_state:
        previous_plan = [item.get("name") for item in previous_state.get("bullet_list", []) if item.get("name")]
    
    # Process the answer
    state = flow.answer(user_answer)

    # Persist informations_plan when generated or changed
    current_plan: List[str] = [item.get("name") for item in state.get("bullet_list", []) if item.get("name")]
    if current_plan != previous_plan:
        await persist_informations_plan(state["service_id"], current_plan)
    
    # Persist the first generated markdown as a draft (once)
    if state.get("final_markdown") and not state.get("context_draft_saved", False):
        await persist_quiz_result(state)
        state["context_draft_saved"] = True

    # If user confirmed, persist final version and close session
    if state.get("context_confirmed"):
        await persist_quiz_result(state)
        delete_session(session_id)
    
    return _build_response(state)


async def force_finish_quiz(session_id: str) -> dict:
    """
    Force finish the quiz, generating markdown from current state.
    
    Args:
        session_id: The session ID
        
    Returns:
        The completion response with final markdown
    """
    flow = get_session(session_id)
    if not flow:
        raise ValueError(f"Session not found: {session_id}")
    
    # Force finish
    state = flow.force_finish()

    # Persist informations_plan on force finish as well
    current_plan: List[str] = [item.get("name") for item in state.get("bullet_list", []) if item.get("name")]
    await persist_informations_plan(state["service_id"], current_plan)
    
    # Persist draft markdown and keep session alive for review
    if state.get("final_markdown") and not state.get("context_draft_saved", False):
        await persist_quiz_result(state)
        state["context_draft_saved"] = True
    
    return _build_response(state)


def _build_response(state: QuizState) -> dict:
    """
    Build API response from quiz state.
    
    Args:
        state: The current quiz state
        
    Returns:
        Response dictionary for API
    """
    return {
        "session_id": state["session_id"],
        "service_id": state["service_id"],
        "phase": state["phase"],
        "question": state["current_response"],
        "bullet_list": [
            {
                "name": item["name"],
                "completed": item["completed"],
                "info": item.get("info")
            }
            for item in state.get("bullet_list", [])
        ],
        "is_done": state["is_done"],
        "turn_count": state["turn_count"],
        "max_turns": state["max_turns"],
        "final_markdown": state.get("final_markdown"),
        "error": state.get("error"),
        "has_qdrant_collection": state.get("has_qdrant_collection", False)
    }


async def persist_quiz_result(state: QuizState) -> None:
    """
    Persist the quiz result to the database.
    
    Updates the subscription_services table with:
    - information: The generated markdown
    - config_completed: True
    - activated: True
    - quiz_q_a: The Q&A history
    
    Args:
        state: The final quiz state
    """
    supabase = get_supabase_client()
    
    # Build Q&A history from messages
    qa_history = []
    messages = state.get("messages", [])
    
    i = 0
    while i < len(messages):
        msg = messages[i]
        if msg["role"] == "assistant":
            qa_entry = {"question": msg["content"]}
            # Check if next message is user answer
            if i + 1 < len(messages) and messages[i + 1]["role"] == "user":
                qa_entry["answer"] = messages[i + 1]["content"]
                i += 1
            qa_history.append(qa_entry)
        i += 1
    
    # Update the database
    update_data = {
        "information": state.get("final_markdown", ""),
        "config_completed": True,
        "activated": True,
        "quiz_q_a": qa_history,
        "informations_plan": [item.get("name") for item in state.get("bullet_list", []) if item.get("name")],
    }
    
    supabase.table("subscription_services").update(update_data).eq(
        "service_id", state["service_id"]
    ).execute()


async def persist_informations_plan(service_id: str, informations_plan: List[str]) -> None:
    """Persist the plan (titles only) into subscription_services.informations_plan."""
    supabase = get_supabase_client()
    supabase.table("subscription_services").update({
        "informations_plan": informations_plan,
    }).eq("service_id", service_id).execute()


async def append_quiz_history(service_id: str, question: str, answer: str) -> None:
    """
    Append a Q&A pair to the quiz history in the database.
    
    This is useful for incremental saving during the quiz.
    
    Args:
        service_id: The subscription service ID
        question: The question asked
        answer: The user's answer
    """
    supabase = get_supabase_client()
    
    # Get current history
    result = supabase.table("subscription_services").select("quiz_q_a").eq(
        "service_id", service_id
    ).single().execute()
    
    current_history = result.data.get("quiz_q_a") or []
    current_history.append({"question": question, "answer": answer})
    
    # Update with new entry
    supabase.table("subscription_services").update({
        "quiz_q_a": current_history
    }).eq("service_id", service_id).execute()


async def check_qdrant_collection(service_id: str) -> tuple[bool, Optional[str]]:
    """
    Check if the service has a qdrant collection (meaning scraping was done).
    
    Args:
        service_id: The subscription service ID
        
    Returns:
        Tuple of (has_collection, collection_name)
    """
    supabase = get_supabase_client()
    
    result = supabase.table("subscription_services").select(
        "qdrant_collection"
    ).eq("service_id", service_id).single().execute()
    
    collection_name = result.data.get("qdrant_collection")
    return (collection_name is not None, collection_name)


async def get_service_business_field(service_id: str) -> Optional[str]:
    """
    Get the business field for a service from its related customer.
    
    Args:
        service_id: The subscription service ID
        
    Returns:
        The business field or None
    """
    supabase = get_supabase_client()
    
    # Get service with customer relation
    result = supabase.table("subscription_services").select(
        "customer:customers(business_field)"
    ).eq("service_id", service_id).single().execute()
    
    customer = result.data.get("customer")
    if customer:
        return customer.get("business_field")
    return None
