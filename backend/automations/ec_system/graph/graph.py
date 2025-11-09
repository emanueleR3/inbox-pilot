"""
Email Classification System - Main Graph Configuration

This module builds and configures the LangGraph workflow for email processing.
The workflow handles email classification, information extraction, and storage.
"""

from langgraph.graph import StateGraph

from .state import create_initial_state
from .config import NodeNames
from .nodes import (
    new_mail_node,
    language_detector_node,
    ai_filter_guardrail_node,
    classifier_node,
    router_node,
)

def create_email_classification_graph():
    """
    Creates and configures the email classification workflow graph.
    
    Returns:
        Configured StateGraph instance ready to process emails
    """
    # Initialize state
    initial_state = create_initial_state()
    
    # Create graph
    graph = StateGraph(initial_state)
    
    # Add core workflow nodes
    graph.add_node(NodeNames.NEW_MAIL, new_mail_node)
    graph.add_node(NodeNames.LANGUAGE_DETECTOR, language_detector_node)
    graph.add_node(NodeNames.AI_FILTER_GUARDRAIL, ai_filter_guardrail_node)
    graph.add_node(NodeNames.CLASSIFIER, classifier_node)
    graph.add_node(NodeNames.ROUTER, router_node)
    
    
    # Configure workflow edges
    graph.set_entry_point(NodeNames.NEW_MAIL)
    graph.add_edge(NodeNames.NEW_MAIL, NodeNames.LANGUAGE_DETECTOR)
    graph.add_edge(NodeNames.LANGUAGE_DETECTOR, NodeNames.AI_FILTER_GUARDRAIL)
    graph.add_edge(NodeNames.AI_FILTER_GUARDRAIL, NodeNames.CLASSIFIER)
    graph.add_edge(NodeNames.CLASSIFIER, NodeNames.ROUTER)
    
    return graph


# Create the graph instance
graph = create_email_classification_graph()


def run_workflow():
    """
    Executes the email classification workflow.
    """
    graph.run()


if __name__ == "__main__":
    run_workflow()
