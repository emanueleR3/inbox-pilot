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
    CONFIG_LOADER = "config_loader"
    LANGUAGE_DETECTOR = "language_detector"
    AI_FILTER = "ai_filter"
    GUARDRAIL = "guardrail"
    AI_FILTER_GUARDRAIL = "ai_filter_guardrail"  # Deprecated, kept for compatibility
    SUMMARIZER = "summarizer"
    CLASSIFIER = "classifier"
    ATTACHMENT_EXTRACTOR = "attachment_extractor"
    ATTACHMENT_SUMMARIZER = "attachment_summarizer"
    EVALUATOR = "evaluator"
    PRIORITY_CONTROLLER = "priority_controller"
    ROUTER = "router"
    SUBCATEGORY_ROUTER = "subcategory_router"
    READER = "reader"
    SCHEDULER = "scheduler"
    
    # Subcategory-specific nodes
    HANDLE_OFFER_PROMOTION = "handle_offer_promotion"
    HANDLE_NEWSLETTER = "handle_newsletter"
    HANDLE_EVENT_INVITE = "handle_event_invite"
    HANDLE_PRODUCT_UPDATE = "handle_product_update"
    HANDLE_REQUEST_QUOTE = "handle_request_quote"
    HANDLE_NEW_MESSAGE = "handle_new_message"
    HANDLE_CONNECTION_REQUEST = "handle_connection_request"
    HANDLE_SYSTEM_ALERT = "handle_system_alert"
    HANDLE_SYSTEM_NOTIFICATION = "handle_system_notification"
    HANDLE_SENT_DOCUMENTS = "handle_sent_documents"
    HANDLE_PROVIDE_UPDATE = "handle_provide_update"
    HANDLE_CONFIRM_APPOINTMENT = "handle_confirm_appointment"
    HANDLE_FORWARD_INFO = "handle_forward_info"
    HANDLE_RESPONSE_TO_REQUEST = "handle_response_to_request"
    HANDLE_REQUEST_DOCUMENT = "handle_request_document"
    HANDLE_EVENT_FOLLOWUP = "handle_event_followup"
    HANDLE_INVOICE_OR_RECEIPT = "handle_invoice_or_receipt"
    HANDLE_STATUS_NOTIFICATION = "handle_status_notification"
    HANDLE_TICKET_UPDATE = "handle_ticket_update"
    HANDLE_GENERAL_GREETING = "handle_general_greeting"
    HANDLE_REQUEST_APPOINTMENT = "handle_request_appointment"
    HANDLE_REQUEST_APPOINTMENT_CHANGE = "handle_request_appointment_change"
    HANDLE_REQUEST_STATUS_UPDATE = "handle_request_status_update"
    HANDLE_ASK_FOR_HELP = "handle_ask_for_help"
    HANDLE_GENERAL_INQUIRY = "handle_general_inquiry"
    HANDLE_PAYMENT_ISSUE = "handle_payment_issue"
    HANDLE_CANCEL_APPOINTMENT = "handle_cancel_appointment"
    HANDLE_ORDER_CONFIRMATION = "handle_order_confirmation"
    HANDLE_ACCOUNT_VERIFICATION = "handle_account_verification"
    HANDLE_INTERNAL_NOTE = "handle_internal_note"
    HANDLE_SPAM_OR_UNKNOWN = "handle_spam_or_unknown"
    HANDLE_UNRELATED_CONTENT = "handle_unrelated_content"
    
    # Legacy nodes (kept for backward compatibility)
    EXTRACT_PROMOTION = "extract_promotion"
    EXTRACT_LOCAL_NOTIFICATION = "extract_local_notification"
    EXTRACT_WEB_PROVIDERS = "extract_web_providers"
    EXTRACT_CALENDAR_EVENTS = "extract_calendar_events"
    EXTRACT_TRANSACTION = "extract_transaction"
    EXTRACT_OTHER = "extract_other"
    SAVE_AND_EXIT = "save_and_exit"
