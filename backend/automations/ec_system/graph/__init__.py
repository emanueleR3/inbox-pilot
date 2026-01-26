"""
Email Classification System - Graph Module

This module provides a LangGraph-based workflow for processing and classifying emails.
"""

from .graph import create_email_classification_graph, graph, run_workflow
from .state import EmailState
from .config import EmailCategories, NodeNames, get_llm

__all__ = [
    'create_email_classification_graph',
    'graph',
    'run_workflow',
    'EmailState',
    'EmailCategories',
    'NodeNames',
    'get_llm',
]
