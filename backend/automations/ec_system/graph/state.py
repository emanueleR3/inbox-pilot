"""
State definition for the email classification system.
"""

from typing import Dict, List, Optional, TypedDict


class EmailState(TypedDict):
    """Shared state across all nodes in the workflow."""
    email_body: Optional[str]
    attachments: List[str]
    language: Optional[str]
    category: Optional[str]
    subcategory: Optional[str]
    extracted_info: Optional[Dict]
    notification: Optional[str]


def create_initial_state() -> EmailState:
    """Create initial state with default values."""
    return {
        "email_body": None,
        "attachments": [],
        "language": None,
        "category": None,
        "subcategory": None,
        "extracted_info": None,
        "notification": None
    }
