"""
State definition for the quiz system using LangGraph.
"""

from typing import Dict, List, Optional, TypedDict, Any


class BulletItem(TypedDict):
    """Single item in the bullet list checklist."""
    name: str
    completed: bool
    info: Optional[str]  # Information collected for this item


class QuizState(TypedDict):
    """Shared state across all nodes in the quiz workflow."""
    # Session identifiers
    service_id: str
    session_id: str
    
    # Scraping context
    has_qdrant_collection: bool  # True if user did scraping, False if skipped
    qdrant_collection_name: Optional[str]
    
    # Conversation state
    turn_count: int
    max_turns: int
    
    # Quiz flow state
    phase: str  # "initial_question", "planning", "collecting", "completed"
    
    # Business field (from first question)
    business_field: Optional[str]
    
    # Bullet list checklist
    bullet_list: List[BulletItem]
    
    # Conversation history
    messages: List[Dict[str, str]]  # {"role": "assistant" | "user", "content": str}
    
    # Current AI response
    current_response: Optional[str]
    
    # Final output
    final_markdown: Optional[str]

    # Post-quiz review stage
    context_draft_saved: bool
    context_confirmed: bool
    
    # Status flags
    is_done: bool
    error: Optional[str]


def create_initial_state(
    service_id: str,
    session_id: str,
    has_qdrant_collection: bool = False,
    qdrant_collection_name: Optional[str] = None,
    max_turns: int = 20
) -> QuizState:
    """Create initial state with default values."""
    return {
        "service_id": service_id,
        "session_id": session_id,
        "has_qdrant_collection": has_qdrant_collection,
        "qdrant_collection_name": qdrant_collection_name,
        "turn_count": 0,
        "max_turns": max_turns,
        "phase": "initial_question",
        "business_field": None,
        "bullet_list": [],
        "messages": [],
        "current_response": None,
        "final_markdown": None,

        "context_draft_saved": False,
        "context_confirmed": False,
        "is_done": False,
        "error": None,
    }
