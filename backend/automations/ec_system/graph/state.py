"""
State definition for the email classification system.
"""

from __future__ import annotations

from typing import Annotated, Dict, List, Optional, TypedDict


def _merge_key_entities(left: Optional[dict], right: Optional[dict]) -> dict:
    """Merge function for LangGraph concurrent updates.

    LangGraph raises on concurrent writes to the same key unless the key is
    Annotated with a reducer. Here we deep-merge dicts of lists and de-duplicate
    items while preserving order.
    """
    merged: dict = {}

    if isinstance(left, dict):
        merged.update(left)

    if not isinstance(right, dict):
        return merged

    for category, items in right.items():
        if items is None:
            continue

        existing = merged.get(category)

        if existing is None:
            merged[category] = list(items) if isinstance(items, list) else items
            continue

        if isinstance(existing, list) and isinstance(items, list):
            for item in items:
                if item not in existing:
                    existing.append(item)
            merged[category] = existing
            continue

        # Fallback: keep existing unless empty-ish, otherwise overwrite
        merged[category] = existing if existing not in (None, [], "") else items

    return merged


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
    email_id: Optional[str]  # Email UUID from emails table (for notifications and scheduled_events)
    original_thread_id: Optional[str]  # Original thread ID from email provider (e.g., Gmail thread ID)
    microsoft_message_id: Optional[str]  # Microsoft Graph internal message ID for replies
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
    key_entities: Annotated[Optional[dict], _merge_key_entities]  # Key entities extracted by Reader/InfoReader (merge-safe)
    needs_response: Optional[bool]  # Flag indicating if email requires a response
    automation_executed: bool  # Flag indicating if automation was executed
    # Parallel task barrier flags
    info_task_done: Optional[bool]  # INFO_REQUESTED_TASK branch completed
    appointment_task_done: Optional[bool]  # MANAGE_APPOINTMENT_TASK branch completed
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
    appointment_favorite_day_unavailable: Optional[bool]  # True if favorite day had no slots and weekly slots were returned instead
    # Event details for ICS generation (populated when event is scheduled/rescheduled)
    scheduled_event_details: Optional[Dict]  # Contains: title, start_time, end_time, location, description, attendees, event_code
    # Confirm appointment-specific fields (for CONFIRM_APPOINTMENT subcategory)
    already_scheduled: Optional[bool]  # True if appointment was already scheduled (final confirmation), False if needs scheduling
    confirm_event_code: Optional[str]  # Event code (6 digits) found in conversation for rescheduling
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
    chunked_company_informations: Optional[dict]  # Filtered company information
    correctness_score: Optional[float]  # Correctness score of the email
    needs_review: Optional[bool]  # Flag indicating if email needs review
    low_confidence_classification: Optional[bool]  # Flag for low confidence classification
    review_iteration: Optional[int]  # Counter for writer-reviewer loop iterations
    edit_history: Optional[List[str]]  # History of modification summaries from writer (text descriptions of changes made)
    # Tasks Extractor fields
    list_of_tasks: Optional[List[str]]  # List of tasks extracted from email (INFO_REQUESTED_TASK, MANAGE_APPOINTMENT_TASK)