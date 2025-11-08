"""
Configuration for the email classification system.
"""

from langchain_openai import ChatOpenAI

def get_llm():
    """
    Initialize and return the LLM instance.
    
    Returns:
        Configured OpenAI LLM instance
    """
    return ChatOpenAI(temperature=0.1, model_name="gpt-4o-mini")


class EmailCategories:
    """Email category constants."""
    PROMOTION = "PROMOTION"
    LOCAL_NOTIFICATION = "LOCAL_NOTIFICATION"
    WEB_PROVIDERS = "WEB_PROVIDERS"
    CALENDAR_EVENTS = "CALENDAR_EVENTS"
    TRANSACTION = "TRANSACTION"
    OTHER = "OTHER"


class NodeNames:
    """Node name constants for the workflow graph."""
    NEW_MAIL = "new_mail"
    LANGUAGE_DETECTOR = "language_detector"
    AI_FILTER_GUARDRAIL = "ai_filter_guardrail"
    CLASSIFIER = "classifier"
    ROUTER = "router"
    EXTRACT_PROMOTION = "extract_promotion"
    EXTRACT_LOCAL_NOTIFICATION = "extract_local_notification"
    EXTRACT_WEB_PROVIDERS = "extract_web_providers"
    EXTRACT_CALENDAR_EVENTS = "extract_calendar_events"
    EXTRACT_TRANSACTION = "extract_transaction"
    EXTRACT_OTHER = "extract_other"
    SAVE_AND_EXIT = "save_and_exit"
