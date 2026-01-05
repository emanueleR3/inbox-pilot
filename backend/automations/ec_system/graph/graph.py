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
    moderation_node,
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
    tasks_extractor_node,
    info_reader_node,
    appointment_router_node,
    task_merger_node,
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
    graph.add_node(NodeNames.MODERATION, moderation_node)
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
    graph.add_node(NodeNames.TASKS_EXTRACTOR, tasks_extractor_node)
    graph.add_node(NodeNames.INFO_READER, info_reader_node)
    graph.add_node(NodeNames.APPOINTMENT_ROUTER, appointment_router_node)
    graph.add_node(NodeNames.TASK_MERGER, task_merger_node)
    
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
    graph.add_edge(NodeNames.CONFIG_LOADER, NodeNames.MODERATION)

    # Conditional edge from moderation: continue if not flagged, end if dangerous
    def should_continue_after_moderation(state):
        """Check if workflow should continue after moderation."""
        if state.get("dangerous_email"):
            print(f"🚨 [MODERATION] Dangerous content detected - exiting workflow before any LLM processing")
            return END
        return NodeNames.LANGUAGE_DETECTOR
    
    graph.add_conditional_edges(
        NodeNames.MODERATION,
        should_continue_after_moderation,
        {
            NodeNames.LANGUAGE_DETECTOR: NodeNames.LANGUAGE_DETECTOR,
            END: END
        }
    )

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
    
    graph.add_edge(NodeNames.PRIORITY_CONTROLLER, NodeNames.SUBCATEGORY_ROUTER)
    
    # Subcategory routing function
    def route_to_subcategory(state):
        """Route to appropriate subcategory handler based on subcategory."""
        subcategory = state.get("subcategory", "SPAM_OR_UNKNOWN")
        
        # Check calendar_provider for appointment-related subcategories
        appointment_subcategories = [
            "REQUEST_APPOINTMENT",
            "REQUEST_APPOINTMENT_CHANGE",
            "CANCEL_APPOINTMENT",
            "CONFIRM_APPOINTMENT"
        ]
        
        if subcategory in appointment_subcategories:
            # Get calendar_provider from user_config
            user_config = state.get("user_config", {})
            calendar_provider = user_config.get("calendar_provider")
            
            if calendar_provider is None:
                print(f"❌ [SUBCATEGORY_ROUTER] No calendar provider configured - cannot process {subcategory}")
                state["status"] = "NO_CALENDAR_PROVIDER"
                state["automation_executed"] = True
                return END
        
        if state.get("high_priority_email") and subcategory in appointment_subcategories:
            return END # TODO valutare di continuare i flussi con scheduler

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
        END: END
    }
    
    # Add conditional edge for subcategory routing
    graph.add_conditional_edges(
        NodeNames.SUBCATEGORY_ROUTER,
        route_to_subcategory,
        subcategory_destinations
    )
    
    # Nodes with conditional logic that may need TASKS_EXTRACTOR
    # These check category first, then route to TASKS_EXTRACTOR or END
    def should_route_to_tasks_extractor_or_end(state):
        """Check if node returned state (needs Tasks Extractor) or response (automation executed)."""
        if state.get("automation_executed"):
            return END
        return NodeNames.TASKS_EXTRACTOR
    
    conditional_nodes_to_tasks_extractor = [
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
    
    # Add conditional edges for nodes that go to TASKS_EXTRACTOR
    for node_name in conditional_nodes_to_tasks_extractor:
        graph.add_conditional_edges(
            node_name,
            should_route_to_tasks_extractor_or_end,
            {
                NodeNames.TASKS_EXTRACTOR: NodeNames.TASKS_EXTRACTOR,
                END: END
            }
        )
    
    # Nodes that always automate (always return AutomationExecutedResponse)
    always_automate_nodes = [
        NodeNames.HANDLE_EVENT_INVITE,
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
    
    # Nodes that always go to TASKS_EXTRACTOR (no category check needed)
    always_to_tasks_extractor_nodes = [
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
    
    # These nodes always go to TASKS_EXTRACTOR
    for node_name in always_to_tasks_extractor_nodes:
        graph.add_edge(node_name, NodeNames.TASKS_EXTRACTOR)
    
    # === PARALLEL TASK EXECUTION ROUTING ===
    
    # Route after TASKS_EXTRACTOR based on extracted tasks
    def route_after_tasks_extractor(state):
        """Route based on extracted tasks for parallel execution."""
        tasks = state.get("list_of_tasks", [])
        high_priority = state.get("high_priority_email", False)
        
        print(f"🔀 [TASKS_EXTRACTOR] Routing based on tasks: {tasks}, high_priority={high_priority}")
        
        # If no tasks, end workflow
        if not tasks:
            print(f"   → No tasks to execute, ending workflow")
            state["automation_executed"] = True
            return END
        
        # Determine which branches to execute
        has_info_task = "INFO_REQUESTED_TASK" in tasks
        has_appointment_task = "MANAGE_APPOINTMENT_TASK" in tasks and not high_priority

        # Return list of nodes for parallel execution
        if has_info_task and has_appointment_task:
            print(f"   → Executing BOTH branches in parallel")
            return [NodeNames.INFO_READER, NodeNames.APPOINTMENT_ROUTER]
        elif has_info_task:
            print(f"   → Executing INFO_READER branch only")
            return NodeNames.INFO_READER
        elif has_appointment_task:
            print(f"   → Executing APPOINTMENT_ROUTER branch only")
            return NodeNames.APPOINTMENT_ROUTER
        else:
            # MANAGE_APPOINTMENT_TASK with high_priority goes to END
            print(f"   → No applicable tasks (high_priority appointment), ending workflow")
            state["automation_executed"] = True
            return END
    
    graph.add_conditional_edges(
        NodeNames.TASKS_EXTRACTOR,
        route_after_tasks_extractor,
        {
            NodeNames.INFO_READER: NodeNames.INFO_READER,
            NodeNames.APPOINTMENT_ROUTER: NodeNames.APPOINTMENT_ROUTER,
            END: END
        }
    )

    # INFO branch: INFO_READER -> EXTRACTOR_COMPANY_INFO -> TASK_MERGER
    graph.add_edge(NodeNames.INFO_READER, NodeNames.EXTRACTOR_COMPANY_INFO)
    
    # APPOINTMENT_ROUTER routes to specialized READER based on subcategory
    def route_appointment_by_subcategory(state):
        """Route to appropriate appointment flow based on subcategory."""
        subcategory = state.get("subcategory", "")
        
        appointment_subcategories = [
            "REQUEST_APPOINTMENT",
            "CONFIRM_APPOINTMENT", 
            "REQUEST_APPOINTMENT_CHANGE",
            "CANCEL_APPOINTMENT"
        ]
        
        if subcategory in appointment_subcategories:
            print(f"   → Routing to READER for {subcategory}")
            return NodeNames.READER
        else:
            # Default: go directly to TASK_MERGER
            print(f"   → Subcategory {subcategory} not appointment-related, going to TASK_MERGER")
            return NodeNames.TASK_MERGER
    
    graph.add_conditional_edges(
        NodeNames.APPOINTMENT_ROUTER,
        route_appointment_by_subcategory,
        {
            NodeNames.READER: NodeNames.READER,
            NodeNames.TASK_MERGER: NodeNames.TASK_MERGER
        }
    )
    
    # TASK_MERGER is a barrier: only proceed once all required branches finished.
    def should_continue_after_task_merger(state):
        tasks = state.get("list_of_tasks", []) or []
        high_priority = state.get("high_priority_email", False)

        has_info_task = "INFO_REQUESTED_TASK" in tasks
        has_appointment_task = "MANAGE_APPOINTMENT_TASK" in tasks and not high_priority

        info_done = (not has_info_task) or bool(state.get("info_task_done"))

        if not has_appointment_task:
            appointment_done = True
        else:
            # If subcategory isn't appointment-related, the appointment task is effectively a no-op.
            subcategory = state.get("subcategory", "")
            appointment_subcategories = {
                "REQUEST_APPOINTMENT",
                "CONFIRM_APPOINTMENT",
                "REQUEST_APPOINTMENT_CHANGE",
                "CANCEL_APPOINTMENT",
            }
            appointment_done = (subcategory not in appointment_subcategories) or bool(state.get("appointment_task_done"))

        if info_done and appointment_done:
            return NodeNames.WRITER

        print(
            f"⏳ [TASK_MERGER] Waiting for branches: info_done={info_done}, appointment_done={appointment_done}"
        )
        return END

    graph.add_conditional_edges(
        NodeNames.TASK_MERGER,
        should_continue_after_task_merger,
        {
            NodeNames.WRITER: NodeNames.WRITER,
            END: END,
        },
    )
    
    # Conditional logic for Reader node based on subcategory
    def should_continue_after_reader(state):
        """
        Check if workflow should end with automation or continue based on needs_response.
        For specific subcategories, if needs_response is False, return AutomationExecutedResponse.
        If needs_response is True, continue (momentarily to END).
        EVENT_FOLLOWUP has special behavior: always returns AutomationExecutedResponse with different human_response values.
        REQUEST_APPOINTMENT routes to SCHEDULER node for appointment scheduling.
        CONFIRM_APPOINTMENT routes based on already_scheduled flag:
          - If already_scheduled=True: follow standard flow based on needs_response
          - If already_scheduled=False: route to SCHEDULER for scheduling
        """
        needs_response = state.get("needs_response", True)
        subcategory = state.get("subcategory", "")

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
        
        # Special routing for CONFIRM_APPOINTMENT based on already_scheduled flag and event_code
        if subcategory == "CONFIRM_APPOINTMENT":
            already_scheduled = state.get("already_scheduled", False)
            confirm_event_code = state.get("confirm_event_code")
            
            if already_scheduled:
                # Appointment is already scheduled - follow standard flow based on needs_response
                print(f"✅ [READER] CONFIRM_APPOINTMENT - already_scheduled=True, following standard flow")
                if not needs_response:
                    state["automation_executed"] = True
                    return END
                else:
                    return NodeNames.TASK_MERGER
            else:
                # Appointment not yet scheduled - check if we have an event_code for rescheduling
                if confirm_event_code and len(confirm_event_code) == 6 and confirm_event_code.isdigit():
                    # Valid event_code found - route to RESCHEDULER
                    print(f"🔄 [READER] CONFIRM_APPOINTMENT - event_code={confirm_event_code} found, routing to RESCHEDULER")
                    # Copy event_code to change_event_code for rescheduler compatibility
                    state["change_event_code"] = confirm_event_code
                    return NodeNames.RESCHEDULER
                else:
                    # No valid event_code - route to SCHEDULER
                    print(f"📅 [READER] CONFIRM_APPOINTMENT - already_scheduled=False, no event_code, routing to SCHEDULER")
                    return NodeNames.SCHEDULER
        
        # Subcategories that should check needs_response for conditional automation
        conditional_automation_subcategories = {
            "FORWARD_INFO", 
            "RESPONSE_TO_REQUEST",
            "INVOICE_OR_RECEIPT",
            "STATUS_NOTIFICATION",
            "GENERAL_GREETING",
            "PRODUCT_UPDATE"  # Skip response for automatic system notifications
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
        return NodeNames.TASK_MERGER
    
    # Add conditional edge from READER
    graph.add_conditional_edges(
        NodeNames.READER,
        should_continue_after_reader,
        {
            NodeNames.SCHEDULER: NodeNames.SCHEDULER,
            NodeNames.RESCHEDULER: NodeNames.RESCHEDULER,
            NodeNames.CANCELLATION: NodeNames.CANCELLATION,
            NodeNames.TASK_MERGER: NodeNames.TASK_MERGER,
            END: END
        }
    )

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

        if state.get("status") in ["EVENT_CODE_INVALID", "EVENT_CODE_NOT_FOUND", "EVENT_CODE_MISSING"]:
            return NodeNames.TASK_MERGER

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
                print(f"✅ [RESCHEDULER] propose_new_slots returned {len(proposed_slots)} slots - Routing to TASK_MERGER")
                return NodeNames.TASK_MERGER
            
        # Case 2: book_appointment was called (scheduled is not None and proposed_slots is None)
        else:
            print(f"📅 [RESCHEDULER] Tool reschedule_appointment called - checking scheduled status")
            
            if scheduled:
                print(f"✅ [RESCHEDULER] Appointment successfully rescheduled - event_code: {event_code} - Routing to TASK_MERGER")
                return NodeNames.TASK_MERGER
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
            NodeNames.TASK_MERGER: NodeNames.TASK_MERGER,
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
                print(f"✅ [SCHEDULER] propose_new_slots returned {len(proposed_slots)} slots - Routing to TASK_MERGER")
                return NodeNames.TASK_MERGER
            
        # Case 2: book_appointment was called (scheduled is not None and proposed_slots is None)
        else:
            print(f"📅 [SCHEDULER] Tool book_appointment called - checking scheduled status")
            
            if scheduled:
                print(f"✅ [SCHEDULER] Appointment successfully scheduled - event_code: {event_code} - Routing to TASK_MERGER")
                return NodeNames.TASK_MERGER
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
            NodeNames.TASK_MERGER: NodeNames.TASK_MERGER,
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
        return NodeNames.TASK_MERGER

    graph.add_conditional_edges(
        NodeNames.CANCELLATION, 
        should_continue_after_cancellation,
        {
            NodeNames.TASK_MERGER: NodeNames.TASK_MERGER,
            END: END
        }
    )


    def should_continue_after_extractor_company_info(state):
        """Route after company info extraction.

        In the parallel tasks flow, company info extraction is part of the INFO
        branch and must converge to TASK_MERGER.
        """
        tasks = state.get("list_of_tasks", []) or []
        in_tasks_flow = "INFO_REQUESTED_TASK" in tasks

        if state.get("status") == "COMPANY_INFO_EXTRACTION_FAILED":
            # In tasks flow, allow other tasks (e.g., appointment) to continue.
            return NodeNames.TASK_MERGER if in_tasks_flow else END

        return NodeNames.TASK_MERGER if in_tasks_flow else NodeNames.WRITER

    graph.add_conditional_edges(
        NodeNames.EXTRACTOR_COMPANY_INFO,
        should_continue_after_extractor_company_info,
        {
            NodeNames.TASK_MERGER: NodeNames.TASK_MERGER,
            NodeNames.WRITER: NodeNames.WRITER,
            END: END
        }
    )

    # Writer to Reviewer edge - always goes to reviewer after first write
    graph.add_edge(NodeNames.WRITER, NodeNames.REVIEWER)

    def should_continue_after_reviewer(state):
        """
        Check reviewer results and decide whether to loop back to writer or continue to sender.
        Logic for status updates is now in reviewer_node.
        """
        if state.get("automation_executed"):
            return END
        
        # If not automated/ended, it means we need to loop
        return NodeNames.WRITER

    graph.add_conditional_edges(
        NodeNames.REVIEWER,
        should_continue_after_reviewer,
        {
            NodeNames.WRITER: NodeNames.WRITER,
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
                "email_id": email_data.get("email_id", None),
                "original_thread_id": email_data.get("original_thread_id", None),
                "microsoft_message_id": email_data.get("microsoft_message_id", None),
                "review_iteration": 0,
                "edit_history": []
            }
        else:
            # Create default initial state
            return {"status": "FAILED", "error": "No email data provided"}
            
        print(f"🎯 [WORKFLOW] Starting with mode summarizer_only={initial_state.get('summarizer_only', False)} and original thread_id={initial_state.get('original_thread_id', None)}")
        
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
            if result is not None:
                process_automation_result(result)
            else:
                print("❌ [WORKFLOW] Skipping automation result processing: result is None")
        except Exception as e:
            print(f"❌ [WORKFLOW] Error processing automation result: {e}")


# Create the graph instance
graph = create_email_classification_graph()

if __name__ == "__main__":
    run_workflow()
