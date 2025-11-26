"""
Email Classification System - Main Graph Configuration

This module builds and configures the LangGraph workflow for email processing.
The workflow handles email classification, information extraction, and storage.
"""

import os
from dotenv import load_dotenv

load_dotenv()  

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "corretto-email-classification")

# Get max iteration for writer-reviewer loop
MAX_REVIEW_ITERATIONS = int(os.getenv("MAX_REVIEW_ITERATIONS", "3"))
CORRECTNESS_THRESHOLD = float(os.getenv("CORRECTNESS_THRESHOLD", "0.9"))

from langgraph.graph import StateGraph, END

from .config import NodeNames
from ..automation_result_management import process_automation_result
from .nodes import (
    new_mail_node,
    config_loader_node,
    language_detector_node,
    ai_filter_node,
    guardrail_node,
    summarizer_node,
    classifier_node,
    attachment_extractor_node,
    attachment_summarizer_node,
    evaluator_node,
    priority_controller_node,
    router_node,
    subcategory_router_node,
    reader_node,
    scheduler_node,
    rescheduler_node,
    cancellation_node,
    extractor_company_info_node,
    writer_node,
    reviewer_node,
    sender_node,
    # Subcategory handler nodes
    handle_offer_promotion_node,
    handle_newsletter_node,
    handle_event_invite_node,
    handle_product_update_node,
    handle_request_quote_node,
    handle_new_message_node,
    handle_connection_request_node,
    handle_system_alert_node,
    handle_system_notification_node,
    handle_sent_documents_node,
    handle_provide_update_node,
    handle_confirm_appointment_node,
    handle_forward_info_node,
    handle_response_to_request_node,
    handle_request_document_node,
    handle_event_followup_node,
    handle_invoice_or_receipt_node,
    handle_status_notification_node,
    handle_ticket_update_node,
    handle_general_greeting_node,
    handle_request_appointment_node,
    handle_request_appointment_change_node,
    handle_request_status_update_node,
    handle_ask_for_help_node,
    handle_general_inquiry_node,
    handle_payment_issue_node,
    handle_cancel_appointment_node,
    handle_order_confirmation_node,
    handle_account_verification_node,
    handle_internal_note_node,
    handle_spam_or_unknown_node,
    handle_unrelated_content_node
)

AUTOMATION_ENABLED = os.getenv("AUTOMATION_ENABLED", "true").lower() == "true"

def create_email_classification_graph():
    """
    Creates and configures the email classification workflow graph.
    
    Returns:
        Configured StateGraph instance ready to process emails
    """
    # Create graph with state schema (type definition)
    from .state import EmailState
    graph = StateGraph(EmailState)
    
    # Add core workflow nodes
    graph.add_node(NodeNames.NEW_MAIL, new_mail_node)
    graph.add_node(NodeNames.CONFIG_LOADER, config_loader_node)
    graph.add_node(NodeNames.LANGUAGE_DETECTOR, language_detector_node)
    graph.add_node(NodeNames.AI_FILTER, ai_filter_node)
    graph.add_node(NodeNames.GUARDRAIL, guardrail_node)
    graph.add_node(NodeNames.SUMMARIZER, summarizer_node)
    graph.add_node(NodeNames.CLASSIFIER, classifier_node)
    graph.add_node(NodeNames.ATTACHMENT_EXTRACTOR, attachment_extractor_node)
    graph.add_node(NodeNames.ATTACHMENT_SUMMARIZER, attachment_summarizer_node)
    graph.add_node(NodeNames.EVALUATOR, evaluator_node)
    graph.add_node(NodeNames.PRIORITY_CONTROLLER, priority_controller_node)
    graph.add_node(NodeNames.ROUTER, router_node)
    graph.add_node(NodeNames.SUBCATEGORY_ROUTER, subcategory_router_node)
    graph.add_node(NodeNames.READER, reader_node)
    graph.add_node(NodeNames.SCHEDULER, scheduler_node)
    graph.add_node(NodeNames.RESCHEDULER, rescheduler_node)
    graph.add_node(NodeNames.CANCELLATION, cancellation_node)
    graph.add_node(NodeNames.EXTRACTOR_COMPANY_INFO, extractor_company_info_node)
    graph.add_node(NodeNames.WRITER, writer_node)
    graph.add_node(NodeNames.REVIEWER, reviewer_node)
    graph.add_node(NodeNames.SENDER, sender_node)
    
    # Add subcategory handler nodes
    graph.add_node(NodeNames.HANDLE_OFFER_PROMOTION, handle_offer_promotion_node)
    graph.add_node(NodeNames.HANDLE_NEWSLETTER, handle_newsletter_node)
    graph.add_node(NodeNames.HANDLE_EVENT_INVITE, handle_event_invite_node)
    graph.add_node(NodeNames.HANDLE_PRODUCT_UPDATE, handle_product_update_node)
    graph.add_node(NodeNames.HANDLE_REQUEST_QUOTE, handle_request_quote_node)
    graph.add_node(NodeNames.HANDLE_NEW_MESSAGE, handle_new_message_node)
    graph.add_node(NodeNames.HANDLE_CONNECTION_REQUEST, handle_connection_request_node)
    graph.add_node(NodeNames.HANDLE_SYSTEM_ALERT, handle_system_alert_node)
    graph.add_node(NodeNames.HANDLE_SYSTEM_NOTIFICATION, handle_system_notification_node)
    graph.add_node(NodeNames.HANDLE_SENT_DOCUMENTS, handle_sent_documents_node)
    graph.add_node(NodeNames.HANDLE_PROVIDE_UPDATE, handle_provide_update_node)
    graph.add_node(NodeNames.HANDLE_CONFIRM_APPOINTMENT, handle_confirm_appointment_node)
    graph.add_node(NodeNames.HANDLE_FORWARD_INFO, handle_forward_info_node)
    graph.add_node(NodeNames.HANDLE_RESPONSE_TO_REQUEST, handle_response_to_request_node)
    graph.add_node(NodeNames.HANDLE_REQUEST_DOCUMENT, handle_request_document_node)
    graph.add_node(NodeNames.HANDLE_EVENT_FOLLOWUP, handle_event_followup_node)
    graph.add_node(NodeNames.HANDLE_INVOICE_OR_RECEIPT, handle_invoice_or_receipt_node)
    graph.add_node(NodeNames.HANDLE_STATUS_NOTIFICATION, handle_status_notification_node)
    graph.add_node(NodeNames.HANDLE_TICKET_UPDATE, handle_ticket_update_node)
    graph.add_node(NodeNames.HANDLE_GENERAL_GREETING, handle_general_greeting_node)
    graph.add_node(NodeNames.HANDLE_REQUEST_APPOINTMENT, handle_request_appointment_node)
    graph.add_node(NodeNames.HANDLE_REQUEST_APPOINTMENT_CHANGE, handle_request_appointment_change_node)
    graph.add_node(NodeNames.HANDLE_REQUEST_STATUS_UPDATE, handle_request_status_update_node)
    graph.add_node(NodeNames.HANDLE_ASK_FOR_HELP, handle_ask_for_help_node)
    graph.add_node(NodeNames.HANDLE_GENERAL_INQUIRY, handle_general_inquiry_node)
    graph.add_node(NodeNames.HANDLE_PAYMENT_ISSUE, handle_payment_issue_node)
    graph.add_node(NodeNames.HANDLE_CANCEL_APPOINTMENT, handle_cancel_appointment_node)
    graph.add_node(NodeNames.HANDLE_ORDER_CONFIRMATION, handle_order_confirmation_node)
    graph.add_node(NodeNames.HANDLE_ACCOUNT_VERIFICATION, handle_account_verification_node)
    graph.add_node(NodeNames.HANDLE_INTERNAL_NOTE, handle_internal_note_node)
    graph.add_node(NodeNames.HANDLE_SPAM_OR_UNKNOWN, handle_spam_or_unknown_node)
    graph.add_node(NodeNames.HANDLE_UNRELATED_CONTENT, handle_unrelated_content_node)
    
    # Configure workflow edges
    graph.set_entry_point(NodeNames.NEW_MAIL)
    graph.add_edge(NodeNames.NEW_MAIL, NodeNames.CONFIG_LOADER)
    graph.add_edge(NodeNames.CONFIG_LOADER, NodeNames.LANGUAGE_DETECTOR)

    def route_after_language_detector(state):
        if state.get("summarizer_only"):
            return NodeNames.SUMMARIZER
        else:
            return NodeNames.AI_FILTER

    graph.add_conditional_edges(
        NodeNames.LANGUAGE_DETECTOR,
        route_after_language_detector,
        {
            NodeNames.AI_FILTER: NodeNames.AI_FILTER,
            NodeNames.SUMMARIZER: NodeNames.SUMMARIZER,
        }
    )

    graph.add_edge(NodeNames.AI_FILTER, NodeNames.GUARDRAIL)

    # Conditional edge from guardrail: continue if safe, end if dangerous
    def should_continue_after_guardrail(state):
        """Check if workflow should continue after guardrail."""
        if state.get("dangerous_email"):
            return END
        return NodeNames.SUMMARIZER
    
    graph.add_conditional_edges(
        NodeNames.GUARDRAIL,
        should_continue_after_guardrail,
        {
            NodeNames.SUMMARIZER: NodeNames.SUMMARIZER,
            END: END
        }
    )

    def route_after_summarizer(state):
        if state.get("summarizer_only"):
            if state.get("has_attachments"):
                return NodeNames.ATTACHMENT_EXTRACTOR
            else:
                return END
        else:
            return NodeNames.CLASSIFIER
    
    graph.add_conditional_edges(
        NodeNames.SUMMARIZER,
        route_after_summarizer,
        {
            NodeNames.CLASSIFIER: NodeNames.CLASSIFIER,
            NodeNames.ATTACHMENT_EXTRACTOR: NodeNames.ATTACHMENT_EXTRACTOR,
            END: END
        }
    )# Edge from summarizer to classifier
    
    
    # Conditional edge from classifier: check confidence and whether attachments are required
    def should_continue_after_classifier(state):
        """Check if workflow should continue after classifier and route based on the
        `must_see_attachments` flag set by the classifier. If the classifier marked
        attachments as essential for understanding/responding, go to the extractor.
        Otherwise continue to the router.
        """
        if state.get("low_confidence_classification"):
            return END

        # Route to attachment extractor only when classifier determined attachments
        # are necessary for correct handling of the message.
        if state.get("must_see_attachments", False):
            return NodeNames.ATTACHMENT_EXTRACTOR

        return NodeNames.ROUTER
    
    graph.add_conditional_edges(
        NodeNames.CLASSIFIER,
        should_continue_after_classifier,
        {
            NodeNames.ATTACHMENT_EXTRACTOR: NodeNames.ATTACHMENT_EXTRACTOR,
            NodeNames.ROUTER: NodeNames.ROUTER,
            END: END
        }
    )
    
    # Edge from attachment extractor to attachment summarizer
    graph.add_edge(NodeNames.ATTACHMENT_EXTRACTOR, NodeNames.ATTACHMENT_SUMMARIZER)
    
    def should_continue_after_attachment_summarizer(state):
        if state.get("summarizer_only"):
            return END
        return NodeNames.ROUTER
    
    graph.add_conditional_edges(
        NodeNames.ATTACHMENT_SUMMARIZER,
        should_continue_after_attachment_summarizer,
        {
            NodeNames.ROUTER: NodeNames.ROUTER,
            END: END
        }
    )
    
    # Edge from router to evaluator
    graph.add_edge(NodeNames.ROUTER, NodeNames.EVALUATOR)
    
    def should_continue_after_evaluator(state):
        """Check if workflow should continue after evaluator."""
        if state.get("low_confidence_classification"):
            return END
        return NodeNames.PRIORITY_CONTROLLER
    
    graph.add_conditional_edges(
        NodeNames.EVALUATOR,
        should_continue_after_evaluator,
        {
            NodeNames.PRIORITY_CONTROLLER: NodeNames.PRIORITY_CONTROLLER,
            END: END
        }
    )
    
    # Conditional edge from priority controller: check priority score
    def should_continue_after_priority_check(state):
        """Check if workflow should end (high priority) or continue to subcategory routing."""
        status = state.get("status", "")
        
        if status == "END_HIGH_PRIORITY":
            return NodeNames.READER
        else:
            return NodeNames.SUBCATEGORY_ROUTER
    
    graph.add_conditional_edges(
        NodeNames.PRIORITY_CONTROLLER,
        should_continue_after_priority_check,
        {
            NodeNames.SUBCATEGORY_ROUTER: NodeNames.SUBCATEGORY_ROUTER,
            NodeNames.READER: NodeNames.READER
        }
    )
    
    # Subcategory routing function
    def route_to_subcategory(state):
        """Route to appropriate subcategory handler based on subcategory."""
        subcategory = state.get("subcategory", "SPAM_OR_UNKNOWN")
        
        # Map subcategories to node names
        subcategory_mapping = {
            "OFFER_PROMOTION": NodeNames.HANDLE_OFFER_PROMOTION,
            "NEWSLETTER": NodeNames.HANDLE_NEWSLETTER,
            "EVENT_INVITE": NodeNames.HANDLE_EVENT_INVITE,
            "PRODUCT_UPDATE": NodeNames.HANDLE_PRODUCT_UPDATE,
            "REQUEST_QUOTE": NodeNames.HANDLE_REQUEST_QUOTE,
            "NEW_MESSAGE": NodeNames.HANDLE_NEW_MESSAGE,
            "CONNECTION_REQUEST": NodeNames.HANDLE_CONNECTION_REQUEST,
            "SYSTEM_ALERT": NodeNames.HANDLE_SYSTEM_ALERT,
            "SYSTEM_NOTIFICATION": NodeNames.HANDLE_SYSTEM_NOTIFICATION,
            "SENT_DOCUMENTS": NodeNames.HANDLE_SENT_DOCUMENTS,
            "PROVIDE_UPDATE": NodeNames.HANDLE_PROVIDE_UPDATE,
            "CONFIRM_APPOINTMENT": NodeNames.HANDLE_CONFIRM_APPOINTMENT,
            "FORWARD_INFO": NodeNames.HANDLE_FORWARD_INFO,
            "RESPONSE_TO_REQUEST": NodeNames.HANDLE_RESPONSE_TO_REQUEST,
            "REQUEST_DOCUMENT": NodeNames.HANDLE_REQUEST_DOCUMENT,
            "EVENT_FOLLOWUP": NodeNames.HANDLE_EVENT_FOLLOWUP,
            "INVOICE_OR_RECEIPT": NodeNames.HANDLE_INVOICE_OR_RECEIPT,
            "STATUS_NOTIFICATION": NodeNames.HANDLE_STATUS_NOTIFICATION,
            "TICKET_UPDATE": NodeNames.HANDLE_TICKET_UPDATE,
            "GENERAL_GREETING": NodeNames.HANDLE_GENERAL_GREETING,
            "REQUEST_APPOINTMENT": NodeNames.HANDLE_REQUEST_APPOINTMENT,
            "REQUEST_APPOINTMENT_CHANGE": NodeNames.HANDLE_REQUEST_APPOINTMENT_CHANGE,
            "REQUEST_STATUS_UPDATE": NodeNames.HANDLE_REQUEST_STATUS_UPDATE,
            "ASK_FOR_HELP": NodeNames.HANDLE_ASK_FOR_HELP,
            "GENERAL_INQUIRY": NodeNames.HANDLE_GENERAL_INQUIRY,
            "PAYMENT_ISSUE": NodeNames.HANDLE_PAYMENT_ISSUE,
            "CANCEL_APPOINTMENT": NodeNames.HANDLE_CANCEL_APPOINTMENT,
            "ORDER_CONFIRMATION": NodeNames.HANDLE_ORDER_CONFIRMATION,
            "ACCOUNT_VERIFICATION": NodeNames.HANDLE_ACCOUNT_VERIFICATION,
            "INTERNAL_NOTE": NodeNames.HANDLE_INTERNAL_NOTE,
            "SPAM_OR_UNKNOWN": NodeNames.HANDLE_SPAM_OR_UNKNOWN,
            "UNRELATED_CONTENT": NodeNames.HANDLE_UNRELATED_CONTENT,
        }
        
        target_node = subcategory_mapping.get(subcategory, NodeNames.HANDLE_SPAM_OR_UNKNOWN)
        print(f"🔀 [SUBCATEGORY_ROUTER] Routing {subcategory} -> {target_node}")
        return target_node
    
    # Create mapping dictionary for all possible subcategory destinations
    subcategory_destinations = {
        NodeNames.HANDLE_OFFER_PROMOTION: NodeNames.HANDLE_OFFER_PROMOTION,
        NodeNames.HANDLE_NEWSLETTER: NodeNames.HANDLE_NEWSLETTER,
        NodeNames.HANDLE_EVENT_INVITE: NodeNames.HANDLE_EVENT_INVITE,
        NodeNames.HANDLE_PRODUCT_UPDATE: NodeNames.HANDLE_PRODUCT_UPDATE,
        NodeNames.HANDLE_REQUEST_QUOTE: NodeNames.HANDLE_REQUEST_QUOTE,
        NodeNames.HANDLE_NEW_MESSAGE: NodeNames.HANDLE_NEW_MESSAGE,
        NodeNames.HANDLE_CONNECTION_REQUEST: NodeNames.HANDLE_CONNECTION_REQUEST,
        NodeNames.HANDLE_SYSTEM_ALERT: NodeNames.HANDLE_SYSTEM_ALERT,
        NodeNames.HANDLE_SYSTEM_NOTIFICATION: NodeNames.HANDLE_SYSTEM_NOTIFICATION,
        NodeNames.HANDLE_SENT_DOCUMENTS: NodeNames.HANDLE_SENT_DOCUMENTS,
        NodeNames.HANDLE_PROVIDE_UPDATE: NodeNames.HANDLE_PROVIDE_UPDATE,
        NodeNames.HANDLE_CONFIRM_APPOINTMENT: NodeNames.HANDLE_CONFIRM_APPOINTMENT,
        NodeNames.HANDLE_FORWARD_INFO: NodeNames.HANDLE_FORWARD_INFO,
        NodeNames.HANDLE_RESPONSE_TO_REQUEST: NodeNames.HANDLE_RESPONSE_TO_REQUEST,
        NodeNames.HANDLE_REQUEST_DOCUMENT: NodeNames.HANDLE_REQUEST_DOCUMENT,
        NodeNames.HANDLE_EVENT_FOLLOWUP: NodeNames.HANDLE_EVENT_FOLLOWUP,
        NodeNames.HANDLE_INVOICE_OR_RECEIPT: NodeNames.HANDLE_INVOICE_OR_RECEIPT,
        NodeNames.HANDLE_STATUS_NOTIFICATION: NodeNames.HANDLE_STATUS_NOTIFICATION,
        NodeNames.HANDLE_TICKET_UPDATE: NodeNames.HANDLE_TICKET_UPDATE,
        NodeNames.HANDLE_GENERAL_GREETING: NodeNames.HANDLE_GENERAL_GREETING,
        NodeNames.HANDLE_REQUEST_APPOINTMENT: NodeNames.HANDLE_REQUEST_APPOINTMENT,
        NodeNames.HANDLE_REQUEST_APPOINTMENT_CHANGE: NodeNames.HANDLE_REQUEST_APPOINTMENT_CHANGE,
        NodeNames.HANDLE_REQUEST_STATUS_UPDATE: NodeNames.HANDLE_REQUEST_STATUS_UPDATE,
        NodeNames.HANDLE_ASK_FOR_HELP: NodeNames.HANDLE_ASK_FOR_HELP,
        NodeNames.HANDLE_GENERAL_INQUIRY: NodeNames.HANDLE_GENERAL_INQUIRY,
        NodeNames.HANDLE_PAYMENT_ISSUE: NodeNames.HANDLE_PAYMENT_ISSUE,
        NodeNames.HANDLE_CANCEL_APPOINTMENT: NodeNames.HANDLE_CANCEL_APPOINTMENT,
        NodeNames.HANDLE_ORDER_CONFIRMATION: NodeNames.HANDLE_ORDER_CONFIRMATION,
        NodeNames.HANDLE_ACCOUNT_VERIFICATION: NodeNames.HANDLE_ACCOUNT_VERIFICATION,
        NodeNames.HANDLE_INTERNAL_NOTE: NodeNames.HANDLE_INTERNAL_NOTE,
        NodeNames.HANDLE_SPAM_OR_UNKNOWN: NodeNames.HANDLE_SPAM_OR_UNKNOWN,
        NodeNames.HANDLE_UNRELATED_CONTENT: NodeNames.HANDLE_UNRELATED_CONTENT,
    }
    
    # Add conditional edge for subcategory routing
    graph.add_conditional_edges(
        NodeNames.SUBCATEGORY_ROUTER,
        route_to_subcategory,
        subcategory_destinations
    )
    
    # Conditional edges for nodes that may route to READER
    # These nodes return state (go to READER) or AutomationExecutedResponse (go to END)
    def should_route_to_reader_or_end(state):
        """Check if node returned state (needs Reader) or response (automation executed)."""
        if state.get("automation_executed"):
            return END
        # Otherwise, the node returned state and needs Reader processing
        return NodeNames.READER
    
    # Nodes with conditional logic that may need Reader
    conditional_nodes = [
        NodeNames.HANDLE_EVENT_INVITE,
        NodeNames.HANDLE_PRODUCT_UPDATE,
        NodeNames.HANDLE_CONNECTION_REQUEST,
        NodeNames.HANDLE_SENT_DOCUMENTS,
        NodeNames.HANDLE_PROVIDE_UPDATE,
        NodeNames.HANDLE_REQUEST_STATUS_UPDATE,
        NodeNames.HANDLE_ASK_FOR_HELP,
        NodeNames.HANDLE_INVOICE_OR_RECEIPT,
        NodeNames.HANDLE_STATUS_NOTIFICATION,
        NodeNames.HANDLE_TICKET_UPDATE
    ]
    
    # Add conditional edges for these nodes
    for node_name in conditional_nodes:
        graph.add_conditional_edges(
            node_name,
            should_route_to_reader_or_end,
            {
                NodeNames.READER: NodeNames.READER,
                END: END
            }
        )
    
    # Nodes that always automate (always return AutomationExecutedResponse)
    always_automate_nodes = [
        NodeNames.HANDLE_OFFER_PROMOTION,
        NodeNames.HANDLE_NEWSLETTER,
        NodeNames.HANDLE_NEW_MESSAGE, 
        NodeNames.HANDLE_SYSTEM_ALERT, 
        NodeNames.HANDLE_SYSTEM_NOTIFICATION, 
        NodeNames.HANDLE_ORDER_CONFIRMATION,
        NodeNames.HANDLE_ACCOUNT_VERIFICATION,
        NodeNames.HANDLE_INTERNAL_NOTE,
        NodeNames.HANDLE_SPAM_OR_UNKNOWN,
        NodeNames.HANDLE_UNRELATED_CONTENT,
        NodeNames.HANDLE_PAYMENT_ISSUE,
        # momentaneamente anche questi TODO
        NodeNames.HANDLE_REQUEST_QUOTE,
        NodeNames.HANDLE_REQUEST_DOCUMENT
    ]
    
    # These nodes always go to END
    for node_name in always_automate_nodes:
        graph.add_edge(node_name, END)
    
    # Nodes that always need Reader or manual handling (return state)
    always_need_manual_nodes = [
        NodeNames.HANDLE_CONFIRM_APPOINTMENT,
        NodeNames.HANDLE_FORWARD_INFO,
        NodeNames.HANDLE_RESPONSE_TO_REQUEST,
        NodeNames.HANDLE_EVENT_FOLLOWUP,
        NodeNames.HANDLE_GENERAL_GREETING,
        NodeNames.HANDLE_GENERAL_INQUIRY,
        NodeNames.HANDLE_REQUEST_APPOINTMENT,
        NodeNames.HANDLE_REQUEST_APPOINTMENT_CHANGE,
        NodeNames.HANDLE_CANCEL_APPOINTMENT
    ]
    
    # These nodes always go to READER for analysis
    for node_name in always_need_manual_nodes:
        graph.add_edge(node_name, NodeNames.READER)
    
    # Conditional logic for Reader node based on needs_response and subcategory
    def should_continue_after_reader(state):
        """
        Check if workflow should end with automation or continue based on needs_response.
        For specific subcategories, if needs_response is False, return AutomationExecutedResponse.
        If needs_response is True, continue (momentarily to END).
        EVENT_FOLLOWUP has special behavior: always returns AutomationExecutedResponse with different human_response values.
        REQUEST_APPOINTMENT routes to SCHEDULER node for appointment scheduling.
        """
        needs_response = state.get("needs_response", True)
        subcategory = state.get("subcategory", "")
        workflow_decision = state.get("workflow_decision", "END_HIGH_PRIORITY")
        
        if workflow_decision == "END_HIGH_PRIORITY":
            return NodeNames.EXTRACTOR_COMPANY_INFO

        # Special routing for REQUEST_APPOINTMENT - goes to SCHEDULER
        if subcategory == "REQUEST_APPOINTMENT":
            print(f"📅 [READER] Routing to SCHEDULER for REQUEST_APPOINTMENT")
            return NodeNames.SCHEDULER
        
        # Special routing for REQUEST_APPOINTMENT_CHANGE - goes to RESCHEDULER
        if subcategory == "REQUEST_APPOINTMENT_CHANGE":
            print(f"🔄 [READER] Routing to RESCHEDULER for REQUEST_APPOINTMENT_CHANGE")
            return NodeNames.RESCHEDULER

        if subcategory == "CANCEL_APPOINTMENT":
            print(f"❌ [READER] Routing to CANCEL_APPOINTMENT for CANCEL_APPOINTMENT")
            return NodeNames.CANCELLATION
        
        # Subcategories that should check needs_response for conditional automation
        conditional_automation_subcategories = {
            "CONFIRM_APPOINTMENT",
            "FORWARD_INFO", 
            "RESPONSE_TO_REQUEST",
            "INVOICE_OR_RECEIPT",
            "STATUS_NOTIFICATION",
            "GENERAL_GREETING"
        }
        
        # Special handling for EVENT_FOLLOWUP - always automate but with different human_response values
        if subcategory == "EVENT_FOLLOWUP":
            if needs_response:
                state["human_response"] = True
                state["status"] = "EVENT_FOLLOWUP_HUMAN_RESPONSE_REQUIRED"
                state["automation_executed"] = True
            else:
                state["automation_executed"] = True
            
            return END
        
        # If subcategory is in the conditional list and doesn't need response, automate
        if subcategory in conditional_automation_subcategories and not needs_response:
            state["automation_executed"] = True
            return END
        
        # For all other cases (needs_response=True or other subcategories), continue manually
        return NodeNames.EXTRACTOR_COMPANY_INFO
    
    # Add conditional edge from READER
    graph.add_conditional_edges(
        NodeNames.READER,
        should_continue_after_reader,
        {
            NodeNames.SCHEDULER: NodeNames.SCHEDULER,
            NodeNames.RESCHEDULER: NodeNames.RESCHEDULER,
            NodeNames.CANCELLATION: NodeNames.CANCELLATION,
            NodeNames.EXTRACTOR_COMPANY_INFO: NodeNames.EXTRACTOR_COMPANY_INFO,
            END: END
        }
    )
    
    # Conditional logic for Scheduler node based on tool called and results
    def should_continue_after_scheduler(state):
        """
        Check scheduler results and create appropriate AutomationExecutedResponse.
        Routes based on which tool was called (propose_new_slots vs book_appointment)
        and the results obtained.
        """
        # Get scheduler results
        scheduled = state.get("appointment_scheduled", False)
        event_code = state.get("appointment_event_code")
        proposed_slots = state.get("appointment_proposed_slots", None)
        
        # Case 1: propose_new_slots was called (proposed_slots is not None)
        if proposed_slots is not None:
            print(f"📅 [SCHEDULER] Tool propose_new_slots called - checking results")
            
            # Check if array is empty
            if not proposed_slots or len(proposed_slots) == 0:
                state["status"] = "NO_AVAILABLE_SLOTS"
                state["human_response"] = True
                state["automation_executed"] = True
                return END
            else:
                print(f"✅ [SCHEDULER] propose_new_slots returned {len(proposed_slots)} slots - Routing to Extractor Company Info")
                return NodeNames.EXTRACTOR_COMPANY_INFO
            
        # Case 2: book_appointment was called (scheduled is not None and proposed_slots is None)
        else:
            print(f"📅 [SCHEDULER] Tool book_appointment called - checking scheduled status")
            
            if scheduled:
                print(f"✅ [SCHEDULER] Appointment successfully scheduled - event_code: {event_code} - Routing to Extractor Company Info")
                return NodeNames.EXTRACTOR_COMPANY_INFO
            else:
                state["status"] = "APPOINTMENT_NOT_SCHEDULED"
                state["human_response"] = True
                state["automation_executed"] = True
                return END

    # Add conditional edge from SCHEDULER
    graph.add_conditional_edges(
        NodeNames.SCHEDULER,
        should_continue_after_scheduler,
        {
            NodeNames.EXTRACTOR_COMPANY_INFO: NodeNames.EXTRACTOR_COMPANY_INFO,
            END: END
        }
    )

    # Conditional logic for Cancellation node based on tool called and results
    def should_continue_after_cancellation(state):
        """
        Check cancellation results and create appropriate AutomationExecutedResponse.
        Routes based on which tool was called (cancel_appointment)
        and the results obtained.
        """
        if state.get("automation_executed"):
            return END
        return NodeNames.EXTRACTOR_COMPANY_INFO

    graph.add_conditional_edges(
        NodeNames.CANCELLATION, 
        should_continue_after_cancellation,
        {
            NodeNames.EXTRACTOR_COMPANY_INFO: NodeNames.EXTRACTOR_COMPANY_INFO,
            END: END
        }
    )


    def should_continue_after_extractor_company_info(state):
        """
        Check extractor company info results and create appropriate AutomationExecutedResponse.
        Routes based on which tool was called (propose_new_slots vs reschedule_appointment)
        and the results obtained.
        """
        if state.get("status") == "COMPANY_INFO_EXTRACTION_FAILED":
            return END
        return NodeNames.WRITER

    graph.add_conditional_edges(
        NodeNames.EXTRACTOR_COMPANY_INFO,
        should_continue_after_extractor_company_info,
        {
            NodeNames.WRITER: NodeNames.WRITER,
            END: END
        }
    )

    # Writer to Reviewer edge - always goes to reviewer after first write
    graph.add_edge(NodeNames.WRITER, NodeNames.REVIEWER)

    def should_continue_after_reviewer(state):
        """
        Check reviewer results and decide whether to loop back to writer or continue to sender.
        
        Loop conditions:
        - needs_review is True AND correctness_score < CORRECTNESS_THRESHOLD (0.9)
        - review_iteration < MAX_REVIEW_ITERATIONS
        
        If loop conditions are not met, continue to sender.
        """
        # TODO momentaneo
        print(f"📝 [REVIEWER] Checking review results: {state.get('written_email_body')}")
        return END
        # ===============

        needs_review = state.get("needs_review", False)
        correctness_score = state.get("correctness_score", 1.0)
        review_iteration = state.get("review_iteration", 0)
        
        # Check if we should loop back to writer
        should_loop = (
            needs_review and 
            correctness_score < CORRECTNESS_THRESHOLD and 
            review_iteration < MAX_REVIEW_ITERATIONS
        )
        
        if should_loop:
            print(f"🔁 [REVIEWER] Looping back to WRITER (iteration {review_iteration + 1})")
            return NodeNames.WRITER
        else:
            if review_iteration >= MAX_REVIEW_ITERATIONS:
                print(f"⚠️ [REVIEWER] Max iterations reached - continuing to SENDER")
            elif correctness_score >= CORRECTNESS_THRESHOLD:
                print(f"✅ [REVIEWER] Correctness threshold met - continuing to SENDER")
            else:
                print(f"✅ [REVIEWER] No review needed - continuing to SENDER")
            return END

    graph.add_conditional_edges(
        NodeNames.REVIEWER,
        should_continue_after_reviewer,
        {
            NodeNames.WRITER: NodeNames.WRITER,
            END: END
        }
    )

    graph.add_edge(NodeNames.SENDER, END)
    
    # Conditional logic for Rescheduler node based on tool called and results
    def should_continue_after_rescheduler(state):
        """
        Check rescheduler results and create appropriate AutomationExecutedResponse.
        Routes based on which tool was called (propose_new_slots vs reschedule_appointment)
        and the results obtained.
        """
        
        # Get rescheduler results
        scheduled = state.get("appointment_scheduled", False)
        event_code = state.get("appointment_event_code")
        proposed_slots = state.get("appointment_proposed_slots")
        
        if state.get("automation_executed"):
            return END    

        if state.get("status") == "EVENT_CODE_INVALID":
            return NodeNames.EXTRACTOR_COMPANY_INFO

        # Case 1: propose_new_slots was called (proposed_slots is not None)
        if proposed_slots is not None:
            print(f"📅 [RESCHEDULER] Tool propose_new_slots called - checking results")
            
            # Check if array is empty
            if not proposed_slots or len(proposed_slots) == 0:
                state["status"] = "NO_AVAILABLE_SLOTS"
                state["human_response"] = True
                state["automation_executed"] = True
                return END
            else:
                print(f"✅ [RESCHEDULER] propose_new_slots returned {len(proposed_slots)} slots - Routing to Extractor Company Info")
                return NodeNames.EXTRACTOR_COMPANY_INFO
            
        # Case 2: book_appointment was called (scheduled is not None and proposed_slots is None)
        else:
            print(f"📅 [RESCHEDULER] Tool reschedule_appointment called - checking scheduled status")
            
            if scheduled:
                print(f"✅ [RESCHEDULER] Appointment successfully rescheduled - event_code: {event_code} - Routing to Extractor Company Info")
                return NodeNames.EXTRACTOR_COMPANY_INFO
            else:
                state["status"] = "APPOINTMENT_NOT_SCHEDULED"
                state["human_response"] = True
                state["automation_executed"] = True
                return END
    
    # Add conditional edge from RESCHEDULER
    graph.add_conditional_edges(
        NodeNames.RESCHEDULER,
        should_continue_after_rescheduler,
        {
            NodeNames.EXTRACTOR_COMPANY_INFO: NodeNames.EXTRACTOR_COMPANY_INFO,
            END: END
        }
    )
    
    return graph



def run_workflow(email_data: dict = None):
    """
    Executes the email classification workflow.
    
    Args:
        email_data: Dictionary containing email information from broker
                   Expected keys: thread_id, message_id, body, attachment_ids, etc.
    
    Returns:
        Dict with workflow execution result
    """
    
    try:
        result = None

        if not AUTOMATION_ENABLED: 
            result = {"status": "AUTOMATION_DISABLED", "error": "Automation is disabled via configuration."}
            return result
            
        # Create initial state with email data if provided
        if email_data:
            initial_state = {
                "email_body": email_data.get("body"),
                "attachments": email_data.get("attachment_ids", []),
                "language": None,  # Will be detected by language_detector_node
                "category": email_data.get("category"),
                "subcategory": email_data.get("subcategory"),
                "extracted_info": {
                    "thread_id": email_data.get("thread_id"),
                    "message_id": email_data.get("message_id"),
                    "reply_to_id": email_data.get("reply_to_id"),
                    "from": email_data.get("from"),
                    "to": email_data.get("to"),
                    "cc": email_data.get("cc"),
                    "subject": email_data.get("subject"),
                    "box_email": email_data.get("box_email"),
                    "provider": email_data.get("provider"),
                    "has_attachments": email_data.get("has_attachments", False),
                    "extended_summary": email_data.get("extended_summary"),
                    "no_reply": email_data.get("no_reply", False)
                },
                "notification": None,
                "user_config": None,
                "attachments_too_large": False,
                "human_response": False,
                "automation_executed": False,
                "summarizer_only": email_data.get("summarizer_only", False),
                "review_iteration": 0
            }
        else:
            # Create default initial state
            return {"status": "FAILED", "error": "No email data provided"}
            
        print(f"🎯 [WORKFLOW] Starting with initial state:")
        print(f"   📧 Body: {initial_state.get('email_body', 'None')[:100]}...")
        print(f"   📎 Attachments: {len(initial_state.get('attachments', []))}")
        print(f"   🏷️ Category: {initial_state.get('category')}")
        print(f"   🧵 Thread ID: {initial_state.get('extracted_info', {}).get('thread_id')}")
        
        # Compile and execute the workflow
        compiled_graph = graph.compile()
        result = compiled_graph.invoke(initial_state)
        
        print(f"🏁 [WORKFLOW] Completed with result: {result}")
        return result
        
    except Exception as e:
        print(f"❌ [WORKFLOW] Error executing workflow: {e}")
        return {"status": "FAILED", "error": str(e)}
    
    finally:
        print(f"==== Processing result for automation management...")
        try:
            process_automation_result(result)
        except Exception as e:
            print(f"❌ [WORKFLOW] Error processing automation result: {e}")


# Create the graph instance
graph = create_email_classification_graph()

if __name__ == "__main__":
    run_workflow()
