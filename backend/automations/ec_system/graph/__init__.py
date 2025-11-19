"""
Email Classification System - Graph Module

This module provides a LangGraph-based workflow for processing and classifying emails.
"""

from .graph import create_email_classification_graph, graph, run_workflow
from .state import EmailState, create_initial_state
from .config import EmailCategories, NodeNames, get_llm

__all__ = [
    'create_email_classification_graph',
    'graph',
    'run_workflow',
    'EmailState',
    'create_initial_state',
    'EmailCategories',
    'NodeNames',
    'get_llm',
]
