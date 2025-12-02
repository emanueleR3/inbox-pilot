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
    status: Optional[str] # State of the execution flow
    dangerous_email: Optional[bool]  # Flag indicating if email is dangerous
    summarizer_only: Optional[bool]  # Flag to run only summarizer workflow
    human_response: Optional[bool]  # Flag indicating if human response is needed
    original_thread_id: Optional[str]  # Original thread ID from email provider (e.g., Gmail thread ID)
    high_priority_email: Optional[bool]  # Flag indicating if email is high priority
    # NEW: Separated workflow fields
    mail_summary: Optional[str]  # Summary of current email
    extended_summary: Optional[str]  # Extended conversation summary
    confidence_score: Optional[float]  # Classification confidence
    attachment_contents: Optional[List[Dict]]  # Extracted attachment contents
    attachments_too_large: Optional[bool]  # Flag for attachments exceeding size limit
    must_see_attachments: Optional[bool]  # Flag indicating if attachments are essential for understanding/responding
    summary_attachments: Optional[str]  # Discursive summary of all attachment contents
    priority_score: Optional[float]  # Category-specific priority score (0.0-1.0)
    key_entities: Optional[dict]  # Key entities extracted by Reader node (dates, locations, requests, etc.)
    needs_response: Optional[bool]  # Flag indicating if email requires a response
    automation_executed: bool  # Flag indicating if automation was executed
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
    # Appointment change fields (for REQUEST_APPOINTMENT_CHANGE subcategory)
    change_event_code: Optional[str]  # Code of event to modify
    change_new_title: Optional[str]  # New title for appointment
    change_new_date: Optional[str]  # New date for appointment
    change_new_duration: Optional[int]  # New duration in minutes
    change_new_attendees: Optional[List[str]]  # New attendees to add
    change_new_place: Optional[str]  # New location
    change_additional_notes: Optional[str]  # Additional notes
    # Cancellation-specific fields (for CANCELLATION subcategory)
    cancellation_event_code: Optional[str]  # Code of event to cancel
    # Extract info and write email
    guidelines: Optional[List[str]]  # Guidelines for writing the email
    written_email_body: Optional[str]  # Body of the email to write
    chunked_company_informations: Optional[dict]  # Filtered company information  TODO decidere se dict, list o string
    correctness_score: Optional[float]  # Correctness score of the email
    needs_review: Optional[bool]  # Flag indicating if email needs review
    low_confidence_classification: Optional[bool]  # Flag for low confidence classification
    review_iteration: Optional[int]  # Counter for writer-reviewer loop iterations
    edit_history: Optional[List[str]]  # History of modification summaries from writer (text descriptions of changes made)


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
        "summarizer_only": False,
        "human_response": False,
        "original_thread_id": None,
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
        "appointment_proposed_slots": None,
        "change_event_code": None,
        "change_new_title": None,
        "change_new_date": None,
        "change_new_duration": None,
        "change_new_attendees": None,
        "change_new_place": None,
        "change_additional_notes": None,
        "guidelines": None,
        "written_email_body": None,
        "chunked_company_informations": None,
        "correctness_score": None,
        "needs_review": None,
        "review_iteration": 0,
        "edit_history": []
    }
