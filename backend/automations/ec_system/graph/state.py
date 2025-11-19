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
    summary_attachments: Optional[str]  # Discursive summary of all attachment contents
    priority_score: Optional[float]  # Category-specific priority score (0.0-1.0)
    high_priority_email: Optional[bool]  # Flag indicating if email exceeded priority threshold
    workflow_decision: Optional[str]  # Decision for workflow routing (END_HIGH_PRIORITY or ROUTE_TO_SUBCATEGORY)
    key_entities: Optional[dict]  # Key entities extracted by Reader node (dates, locations, requests, etc.)
    needs_response: Optional[bool]  # Flag indicating if email requires a response
    # Appointment-specific fields (for REQUEST_APPOINTMENT subcategory)
    appointment_title: Optional[str]  # Title of the appointment
    appointment_date: Optional[str]  # Date and time of the appointment (YYYY-MM-DDThh:mm:ss)
    appointment_duration: Optional[int]  # Duration in minutes
    appointment_attendees: Optional[List[str]]  # List of attendee emails
    appointment_place: Optional[str]  # Location of the appointment
    appointment_notes: Optional[str]  # Additional notes
    # Scheduler-specific fields (for REQUEST_APPOINTMENT scheduling result)
    appointment_scheduled: Optional[bool]  # True if appointment was successfully booked
    appointment_overlap: Optional[bool]  # True if there's overlap with other events
    appointment_event_code: Optional[str]  # Event code if booked
    appointment_proposed_slots: Optional[List[str]]  # Proposed dates if booking not possible


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
        "must_see_attachments": False,
        "summary_attachments": None,
        "priority_score": None,
        "high_priority_email": False,
        "workflow_decision": None,
        "key_entities": None,
        "needs_response": None,
        "appointment_title": None,
        "appointment_date": None,
        "appointment_duration": None,
        "appointment_attendees": None,
        "appointment_place": None,
        "appointment_notes": None,
        "appointment_scheduled": None,
        "appointment_overlap": None,
        "appointment_event_code": None,
        "appointment_proposed_slots": None
    }
