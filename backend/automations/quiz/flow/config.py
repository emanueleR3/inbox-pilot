"""
Configuration for the quiz system.
"""

import os
from langchain_openai import ChatOpenAI


# Quiz configuration constants
MAX_TURNS = int(os.getenv("QUIZ_MAX_TURNS", "20"))
LLM_MODEL = os.getenv("QUIZ_LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("QUIZ_LLM_TEMPERATURE", "0.7"))


def get_llm(temperature: float = LLM_TEMPERATURE) -> ChatOpenAI:
    """
    Initialize and return the LLM instance.
    
    Args:
        temperature: Model temperature for response creativity
        
    Returns:
        Configured OpenAI LLM instance
    """
    return ChatOpenAI(
        temperature=temperature, 
        model_name=LLM_MODEL,
        api_key=os.getenv("OPENAI_API_KEY")
    )


class NodeNames:
    """Node name constants for the quiz workflow graph."""
    START_QUIZ = "start_quiz"
    CHECK_SCRAPING = "check_scraping"
    INITIAL_QUESTION = "initial_question"
    GENERATE_PLAN = "generate_plan"
    COLLECT_INFO = "collect_info"
    PROCESS_ANSWER = "process_answer"
    CHECK_COMPLETION = "check_completion"
    GENERATE_MARKDOWN = "generate_markdown"
    WITH_CONTEXT = "with_context"  # For users who did scraping


class QuizPhases:
    """Quiz phase constants."""
    INITIAL_QUESTION = "initial_question"
    PLANNING = "planning"
    COLLECTING = "collecting"
    COMPLETED = "completed"
