"""
Quiz Service V2 - Simplified State Machine Approach

This service manages quiz sessions using a simple state machine pattern
instead of LangGraph.
"""
import uuid
from typing import Optional, List, Any

from quiz.flow.quiz_flow import QuizFlow
from quiz.flow.state import QuizState
from db_client import get_supabase_client


_QUIZ_SESSIONS_TABLE = "quiz_sessions"

_QUIZ_SESSION_COLUMNS = (
    "session_id,service_id,email,"
    "has_qdrant,qdrant_collection,"
    "has_qdrant_collection,qdrant_collection_name,"
    "turn_count,max_turns,phase,business_field,"
    "bullet_list,messages,current_response,final_markdown,"
    "context_draft_saved,context_confirmed,conversation_log,pending_context_save,"
    "is_done,error,status,created_at,updated_at,expires_at"
)


def _normalize_session_id(session_id: str) -> str:
    if session_id is None:
        return ""
    return str(session_id).strip().strip('"').strip("'")


def _get_quiz_session_row(session_id: str) -> Optional[dict[str, Any]]:
    """Fetch session row from Supabase.

    Expected table schema:
    - session_id (uuid) PRIMARY KEY
    - service_id (uuid) NOT NULL
    - email (text) NOT NULL
    - QuizState fields as plain columns
    """
    supabase = get_supabase_client()
    session_id = _normalize_session_id(session_id)
    if not session_id:
        return None

    try:
        result = (
            supabase.table(_QUIZ_SESSIONS_TABLE)
            .select(_QUIZ_SESSION_COLUMNS)
            .eq("session_id", session_id)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


def fetch_quiz_session_row(session_id: str) -> Optional[dict[str, Any]]:
    """Public wrapper for fetching a quiz session row."""
    return _get_quiz_session_row(session_id)


def list_quiz_sessions(limit: int = 50, status: Optional[str] = "in_progress") -> list[dict[str, Any]]:
    """List quiz sessions from Supabase.

    Args:
        limit: Max rows to return.
        status: If provided, filters by quiz_sessions.status.
    """
    supabase = get_supabase_client()
    try:
        query = supabase.table(_QUIZ_SESSIONS_TABLE).select(
            "session_id,service_id,email,status,phase,turn_count,max_turns,created_at,updated_at"
        )
        if status:
            query = query.eq("status", status)
        result = query.order("updated_at", desc=True).limit(limit).execute()
        return result.data or []
    except Exception:
        return []


def _get_email_for_service(service_id: str) -> Optional[str]:
    supabase = get_supabase_client()
    if not service_id:
        return None
    try:
        result = (
            supabase.table("subscription_services")
            .select("email")
            .eq("service_id", service_id)
            .single()
            .execute()
        )
        email = (result.data or {}).get("email")
        return email
    except Exception:
        return None


def _row_looks_unstarted(row: dict[str, Any]) -> bool:
    """Heuristic: session created but quiz not started yet."""
    return (
        (row.get("current_response") is None)
        and (row.get("business_field") is None)
        and (row.get("turn_count") in (None, 0))
        and (row.get("messages") in (None, [], {}))
        and (row.get("bullet_list") in (None, [], {}))
    )


def _row_to_state(row: dict[str, Any]) -> QuizState:
    # Ensure JSON columns are always list-shaped
    bullet_list = row.get("bullet_list") or []
    messages = row.get("messages") or []
    conversation_log = row.get("conversation_log") or []

    return {
        "email": row.get("email") or "",
        "session_id": str(row.get("session_id") or ""),
        "has_qdrant_collection": bool(row.get("has_qdrant_collection", False)),
        "qdrant_collection_name": row.get("qdrant_collection_name"),
        "turn_count": int(row.get("turn_count") or 0),
        "max_turns": int(row.get("max_turns") or 20),
        "phase": row.get("phase") or "initial_question",
        "business_field": row.get("business_field"),
        "bullet_list": bullet_list,
        "messages": messages,
        "current_response": row.get("current_response"),
        "final_markdown": row.get("final_markdown"),
        "context_draft_saved": bool(row.get("context_draft_saved", False)),
        "context_confirmed": bool(row.get("context_confirmed", False)),
        "conversation_log": conversation_log,
        "pending_context_save": bool(row.get("pending_context_save", False)),
        "is_done": bool(row.get("is_done", False)),
        "error": row.get("error"),
    }


def _state_to_update_payload(state: QuizState) -> dict[str, Any]:
    # Keep redundant columns consistent
    has_qdrant_collection = bool(state.get("has_qdrant_collection", False))
    qdrant_collection_name = state.get("qdrant_collection_name")

    return {
        "email": state.get("email"),
        "has_qdrant": has_qdrant_collection,
        "qdrant_collection": qdrant_collection_name,
        "has_qdrant_collection": has_qdrant_collection,
        "qdrant_collection_name": qdrant_collection_name,
        "turn_count": state.get("turn_count", 0),
        "max_turns": state.get("max_turns", 20),
        "phase": state.get("phase"),
        "business_field": state.get("business_field"),
        "bullet_list": state.get("bullet_list", []),
        "messages": state.get("messages", []),
        "current_response": state.get("current_response"),
        "final_markdown": state.get("final_markdown"),
        "context_draft_saved": bool(state.get("context_draft_saved", False)),
        "context_confirmed": bool(state.get("context_confirmed", False)),
        "conversation_log": state.get("conversation_log", []),
        "pending_context_save": bool(state.get("pending_context_save", False)),
        "is_done": bool(state.get("is_done", False)),
        "error": state.get("error"),
        "status": "completed" if state.get("is_done") else "in_progress",
    }


def _upsert_quiz_session(session_id: str, service_id: str, email: str) -> None:
    supabase = get_supabase_client()
    session_id = _normalize_session_id(session_id)
    payload: dict[str, Any] = {
        "session_id": session_id,
        "service_id": service_id,
        "email": email,
    }
    supabase.table(_QUIZ_SESSIONS_TABLE).upsert(payload).execute()


def _save_quiz_session_state(session_id: str, state: QuizState) -> None:
    supabase = get_supabase_client()
    session_id = _normalize_session_id(session_id)
    supabase.table(_QUIZ_SESSIONS_TABLE).update(_state_to_update_payload(state)).eq("session_id", session_id).execute()


def create_session(service_id: str) -> str:
    """
    Create a new quiz session for a user (keyed by email).
    
    Args:
        service_id: subscription_services.service_id
        
    Returns:
        The session ID
    """
    email = _get_email_for_service(service_id)
    if not email:
        raise ValueError(f"Unable to find email for service_id: {service_id}")

    session_id = str(uuid.uuid4())
    # Persist the session immediately (state will be filled on start_quiz)
    try:
        _upsert_quiz_session(session_id=session_id, service_id=service_id, email=email)
    except Exception as e:
        raise ValueError(
            f"Unable to persist quiz session to Supabase. Ensure '{_QUIZ_SESSIONS_TABLE}' table exists. Error: {e}"
        )
    return session_id


def get_session(session_id: str) -> Optional[QuizFlow]:
    """
    Get an existing quiz session.
    
    Args:
        session_id: The session ID
        
    Returns:
        The QuizFlow instance or None if not found
    """
    row = _get_quiz_session_row(session_id)
    if not row:
        return None

    flow = QuizFlow(email=row["email"], session_id=row["session_id"])

    # If the quiz was never started, keep flow.state=None (so start_quiz is idempotent)
    if not _row_looks_unstarted(row):
        state = _row_to_state(row)
        flow.set_state(state)
        flow.has_qdrant = bool(state.get("has_qdrant_collection", False))
        flow.qdrant_collection = state.get("qdrant_collection_name")

    return flow


def delete_session(session_id: str) -> bool:
    """
    Delete a quiz session.
    
    Args:
        session_id: The session ID
        
    Returns:
        True if deleted, False if not found
    """
    supabase = get_supabase_client()
    session_id = _normalize_session_id(session_id)
    if not session_id:
        return False

    try:
        # Best-effort existence check (avoid returning True on no-op deletes)
        exists = _get_quiz_session_row(session_id)
        if not exists:
            return False
        supabase.table(_QUIZ_SESSIONS_TABLE).delete().eq("session_id", session_id).execute()
        return True
    except Exception:
        return False


async def start_quiz(service_id: str, session_id: str) -> dict:
    """
    Start a new quiz for a service.
    
    Args:
        service_id: subscription_services.service_id
        session_id: The session ID
        
    Returns:
        The initial quiz response with question and bullet list
    """
    flow = get_session(session_id)
    if not flow:
        raise ValueError(f"Session not found: {session_id}")

    # Safety: session is keyed to a specific service
    row = _get_quiz_session_row(session_id)
    if not row:
        raise ValueError(f"Session not found: {session_id}")
    if service_id and str(row.get("service_id")) != str(service_id):
        raise ValueError(f"Session/service mismatch for session {session_id}")

    # Idempotency: if already started, just return current state
    existing_state = flow.get_state()
    if existing_state:
        return _build_response(existing_state)
    
    # Check if user has qdrant collection (did scraping)
    has_qdrant, qdrant_collection = await check_qdrant_collection(flow.email)
    
    # Update flow with qdrant info
    flow.has_qdrant = has_qdrant
    flow.qdrant_collection = qdrant_collection
    
    # Start the quiz flow
    state = flow.start()

    # Persist state after starting
    _save_quiz_session_state(session_id, state)
    
    # Persist informations_plan on start (especially important for Qdrant flow)
    current_plan: List[str] = [item.get("name") for item in state.get("bullet_list", []) if item.get("name")]
    if current_plan:
        await persist_informations_plan(state["email"], current_plan)
    
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
    session_id = _normalize_session_id(session_id)
    flow = get_session(session_id)
    if not flow:
        raise ValueError(f"Session not found: {session_id}")

    previous_state = flow.get_state()
    if not previous_state:
        raise ValueError("Quiz not started. Call start_quiz first.")

    previous_plan: List[str] = []
    if previous_state:
        previous_plan = [item.get("name") for item in previous_state.get("bullet_list", []) if item.get("name")]
    
    # Process the answer
    state = flow.answer(user_answer)

    # Persist updated state early so quiz_sessions always reflects the latest turn,
    # even if later side-effects (Supabase updates on other tables, context update) fail.
    _save_quiz_session_state(session_id, state)

    # Persist informations_plan when generated or changed
    current_plan: List[str] = [item.get("name") for item in state.get("bullet_list", []) if item.get("name")]
    if current_plan != previous_plan:
        await persist_informations_plan(state["email"], current_plan)
    
    # Persist the first generated markdown as a draft (once)
    if state.get("final_markdown") and not state.get("context_draft_saved", False):
        await persist_quiz_result(state)
        state["context_draft_saved"] = True
        _save_quiz_session_state(session_id, state)

    # If user confirmed, persist final version
    if state.get("context_confirmed"):
        # Consider the quiz completed once the user confirms.
        state["is_done"] = True
        await persist_quiz_result(state)
        
        # If pending_context_save (qdrant user), update JSON and rebuild collection
        if state.get("pending_context_save") and state.get("has_qdrant_collection"):
            try:
                from quiz.flow.context_updater import finalize_context_update
                
                conversation_log = state.get("conversation_log", [])
                final_markdown = state.get("final_markdown", "")
                email = state["email"]
                
                print(f"🔄 [QUIZ_SERVICE] Triggering context update for {email}...")
                success = finalize_context_update(email, conversation_log, final_markdown)
                
                if success:
                    print(f"✅ [QUIZ_SERVICE] Context update completed for {email}")
                else:
                    print(f"⚠️ [QUIZ_SERVICE] Context update failed for {email}")
            except Exception as e:
                print(f"❌ [QUIZ_SERVICE] Error in context update: {e}")

            # Persist final state (completed) to quiz_sessions.
            _save_quiz_session_state(session_id, state)
            return _build_response(state)
    
    return _build_response(state)


async def force_finish_quiz(session_id: str) -> dict:
    """
    Force finish the quiz, generating markdown from current state.
    
    Args:
        session_id: The session ID
        
    Returns:
        The completion response with final markdown
    """
    session_id = _normalize_session_id(session_id)
    flow = get_session(session_id)
    if not flow:
        raise ValueError(f"Session not found: {session_id}")
    
    # Force finish
    state = flow.force_finish()

    # Persist updated state early so quiz_sessions marks the session completed
    # even if later side-effects fail.
    _save_quiz_session_state(session_id, state)

    # Persist informations_plan on force finish as well
    current_plan: List[str] = [item.get("name") for item in state.get("bullet_list", []) if item.get("name")]
    await persist_informations_plan(state["email"], current_plan)
    
    # Persist draft markdown and keep session alive for review
    if state.get("final_markdown") and not state.get("context_draft_saved", False):
        await persist_quiz_result(state)
        state["context_draft_saved"] = True

    # Persist updated state (after local mutations)
    _save_quiz_session_state(session_id, state)
    
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
        "email": state["email"],
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
        "has_qdrant_collection": state.get("has_qdrant_collection", False),
        "conversation_log": state.get("conversation_log", []),
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
        "email", state["email"]
    ).execute()


async def persist_informations_plan(email: str, informations_plan: List[str]) -> None:
    """Persist the plan (titles only) into subscription_services.informations_plan."""
    supabase = get_supabase_client()
    supabase.table("subscription_services").update({
        "informations_plan": informations_plan,
    }).eq("email", email).execute()


async def append_quiz_history(email: str, question: str, answer: str) -> None:
    """
    Append a Q&A pair to the quiz history in the database.
    
    This is useful for incremental saving during the quiz.
    
    Args:
        email: The subscription service email
        question: The question asked
        answer: The user's answer
    """
    supabase = get_supabase_client()
    
    # Get current history
    result = supabase.table("subscription_services").select("quiz_q_a").eq(
        "email", email
    ).single().execute()
    
    current_history = result.data.get("quiz_q_a") or []
    current_history.append({"question": question, "answer": answer})
    
    # Update with new entry
    supabase.table("subscription_services").update({
        "quiz_q_a": current_history
    }).eq("email", email).execute()


async def check_qdrant_collection(email: str) -> tuple[bool, Optional[str]]:
    """
    Check if the service has a qdrant collection (meaning scraping was done).
    
    Args:
        email: The subscription service email
        
    Returns:
        Tuple of (has_collection, collection_name)
    """
    supabase = get_supabase_client()
    
    result = supabase.table("subscription_services").select(
        "qdrant_collection"
    ).eq("email", email).single().execute()
    
    collection_name = result.data.get("qdrant_collection")
    return (collection_name is not None, collection_name)


async def get_service_business_field(email: str) -> Optional[str]:
    """
    Get the business field for a service from its related customer.
    
    Args:
        email: The subscription service email
        
    Returns:
        The business field or None
    """
    supabase = get_supabase_client()
    
    # Get service with customer relation
    result = supabase.table("subscription_services").select(
        "customer:customers(business_field)"
    ).eq("email", email).single().execute()
    
    customer = result.data.get("customer")
    if customer:
        return customer.get("business_field")
    return None
