"""
Core workflow nodes for email processing.
"""

from langgraph.graph import END
from .config import NodeNames
""" from .utils import (
    get_email_body,
    get_attachments,
    detect_language,
    validate_content,
    classify_category,
    notify_admin
) """



def new_mail_node(state):
    """
    Receives and prepares email data.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name: "language_detector"
    """
    #state["email_body"] = get_email_body()
    #state["attachments"] = get_attachments()
    return NodeNames.LANGUAGE_DETECTOR


def language_detector_node(state):
    """
    Detects the language of the email.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name: "ai_filter_guardrail"
    """
    #state["language"] = detect_language(state["email_body"])
    return NodeNames.AI_FILTER_GUARDRAIL


def ai_filter_guardrail_node(state):
    """
    Validates that the content is valid and manageable.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name: "classifier" or END
    """
    ##
    return NodeNames.CLASSIFIER


def classifier_node(state):
    """
    Classifies the email into categories.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name: "router" or END
    """
    #state["category"] = classify_category(state["email_body"], state["language"])

    return NodeNames.ROUTER


def router_node(state):
    """
    Routes to the appropriate data extraction agent.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name based on category
    """
    category = state["category"]
    
    category_routing = {
        "PROMOTION": "extract_promotion",
        "LOCAL_NOTIFICATION": "extract_local_notification",
        "WEB_PROVIDERS": "extract_web_providers",
        "CALENDAR_EVENTS": "extract_calendar_events",
        "TRANSACTION": "extract_transaction"
    }
    
    return category_routing.get(category, "extract_other") 


def save_and_exit_node(state):
    """
    Final node: saves everything to DB and notifies user.
    
    Args:
        state: Current workflow state
        
    Returns:
        END signal
    """
    ##
    
    return END
