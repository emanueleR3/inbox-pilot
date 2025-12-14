"""
Quiz graph module.

Provides a simple state machine approach for the quiz flow.
"""

from .state import QuizState, BulletItem, create_initial_state
from .config import NodeNames, QuizPhases, get_llm, MAX_TURNS
from .quiz_flow import QuizFlow
from .nodes import (
    initial_question_node,
    validate_business_answer_node,
    generate_plan_node,
    process_answer_node,
    check_completion_node,
    generate_markdown_node,
    with_context_node,
)

__all__ = [
    # State
    "QuizState",
    "BulletItem", 
    "create_initial_state",
    # Config
    "NodeNames",
    "QuizPhases",
    "get_llm",
    "MAX_TURNS",
    # Flow
    "QuizFlow",
    # Nodes
    "initial_question_node",
    "validate_business_answer_node",
    "generate_plan_node",
    "process_answer_node",
    "check_completion_node",
    "generate_markdown_node",
    "with_context_node",
]
