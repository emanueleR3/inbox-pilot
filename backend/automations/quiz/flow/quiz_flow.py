"""
Quiz Flow - Simple state-based quiz system.

No need for LangGraph - this is a simple interactive conversation
where we wait for user input between each step.
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT_QUIZ", "corretto_quiz")

from .config import QuizPhases, MAX_TURNS
from .state import QuizState, create_initial_state
from .nodes import (
    initial_question_node,
    validate_business_answer_node,
    generate_plan_node,
    process_answer_node,
    check_completion_node,
    generate_markdown_node,
    with_context_node,
    confirm_business_and_continue_node,
    start_review_context_node,
    edit_context_node,
)


class QuizFlow:
    """
    Simple quiz flow manager.
    
    Handles the quiz conversation step by step, waiting for user input
    between each step. No need for a complex graph structure.
    """
    
    def __init__(self, email: str, session_id: str, has_qdrant: bool = False, qdrant_collection: Optional[str] = None):
        """
        Initialize quiz flow.
        
        Args:
            email: The email (unique key in subscription_services)
            session_id: The session ID
            has_qdrant: Whether user has a qdrant collection (did scraping)
            qdrant_collection: The qdrant collection name if exists
        """
        self.email = email
        self.session_id = session_id
        self.state: Optional[QuizState] = None
        self.has_qdrant = has_qdrant
        self.qdrant_collection = qdrant_collection
    
    def start(self) -> QuizState:
        """
        Start the quiz.
        
        Returns:
            State with initial question or TODO message for context case
        """
        # Create initial state
        self.state = create_initial_state(
            email=self.email,
            session_id=self.session_id,
            has_qdrant_collection=self.has_qdrant,
            qdrant_collection_name=self.qdrant_collection,
            max_turns=MAX_TURNS,
        )
    
        # Step 1: Route based on scraping status
        if self.state["has_qdrant_collection"]:
            # TODO: User has context from scraping
            print(f"✅ User did scraping - collection: {self.state['qdrant_collection_name']}")
            self.state = with_context_node(self.state)
        else:
            # No context - start with initial question
            print(f"⏭️ User skipped scraping - starting from scratch")
            self.state = initial_question_node(self.state)
        
        return self.state
    
    def answer(self, user_answer: str) -> QuizState:
        """
        Process user's answer and return next question or completion.
        
        Args:
            user_answer: The user's response
            
        Returns:
            Updated state with next question or completion status
        """
        if self.state is None:
            raise ValueError("Quiz not started. Call start() first.")
        
        # Content moderation check BEFORE any LLM processing
        try:
            from openai import OpenAI
            import os
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            moderation_response = client.moderations.create(
                model="omni-moderation-latest",
                input=user_answer
            )
            
            result = moderation_response.results[0]
            if result.flagged:
                # Log flagged categories
                try:
                    categories_dict = result.categories.model_dump()
                except AttributeError:
                    categories_dict = dict(result.categories)
                
                flagged_categories = [cat for cat, flagged in categories_dict.items() if flagged]
                print(f"🚨 [QUIZ_MODERATION] Content FLAGGED! Categories: {flagged_categories}")
                
                # Return immediately with error message - don't pass to any LLM
                self.state["current_response"] = "Non posso elaborare richieste di questo genere."
                self.state["messages"].append({
                    "role": "assistant",
                    "content": "Non posso elaborare richieste di questo genere."
                })
                return self.state
            
            print(f"✅ [QUIZ_MODERATION] Content passed moderation check")
            
        except Exception as e:
            print(f"❌ [QUIZ_MODERATION] Error during moderation check: {e}")
            # On error, continue but log for monitoring
        
        # Add user message to history
        self.state["messages"].append({
            "role": "user",
            "content": user_answer
        })
        
        # Route based on current phase
        if self.state["phase"] == QuizPhases.INITIAL_QUESTION:
            # User just described their business - validate first
            self.state["business_field"] = user_answer
            
            # Validate the business description
            self.state, is_valid = validate_business_answer_node(self.state)
            
            # Only generate plan if validation passed
            if is_valid:
                self.state = generate_plan_node(self.state)
            # If not valid, state already has clarification question
        
        elif self.state["phase"] == QuizPhases.CONFIRMING_BUSINESS:
            # User is confirming/correcting the business field extracted from scraping
            self.state = confirm_business_and_continue_node(self.state, user_answer)
            
        elif self.state["phase"] == QuizPhases.COLLECTING:
            # User is answering collection questions
            self.state = process_answer_node(self.state)
            self.state = check_completion_node(self.state)
            
            # If done, generate markdown
            if self.state["is_done"]:
                self.state = generate_markdown_node(self.state)
                # Start review chat
                self.state = start_review_context_node(self.state)

        elif self.state["phase"] == QuizPhases.REVIEWING:
            # Post-quiz review/edit chat
            self.state = edit_context_node(self.state, user_answer)
        
        return self.state
    
    def force_finish(self) -> QuizState:
        """
        Force finish the quiz and generate markdown with current info.
        
        Returns:
            State with final markdown
        """
        if self.state is None:
            raise ValueError("Quiz not started. Call start() first.")
        
        self.state["is_done"] = True
        self.state["phase"] = QuizPhases.COMPLETED
        self.state = generate_markdown_node(self.state)
        self.state = start_review_context_node(self.state)
        return self.state
    
    def get_state(self) -> Optional[QuizState]:
        """Get current state."""
        return self.state
    
    def set_state(self, state: QuizState) -> None:
        """Set state (for restoring from session)."""
        self.state = state


__all__ = [
    "QuizFlow",
]
