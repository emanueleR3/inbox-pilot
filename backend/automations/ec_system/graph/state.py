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
    user_config: Optional[Dict]  # User configuration with thresholds
    # NEW: Separated workflow fields
    mail_summary: Optional[str]  # Summary of current email
    extended_summary: Optional[str]  # Extended conversation summary
    confidence_score: Optional[float]  # Classification confidence
    attachment_contents: Optional[List[Dict]]  # Extracted attachment contents
    attachments_too_large: Optional[bool]  # Flag for attachments exceeding size limit
    must_see_attachments: Optional[bool]  # Flag indicating if attachments are essential for understanding/responding


def create_initial_state() -> EmailState:
    """Create initial state with default values."""
    return {
        "email_body": None,
        "attachments": [],
        "language": None,
        "category": None,
        "subcategory": None,
        "extracted_info": None,
        "notification": None,
        "user_config": None,
        "mail_summary": None,
        "extended_summary": None,
        "confidence_score": None,
        "attachment_contents": None,
        "attachments_too_large": False,
        "must_see_attachments": False
    }
