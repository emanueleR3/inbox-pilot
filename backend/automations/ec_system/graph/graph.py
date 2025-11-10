"""
Email Classification System - Main Graph Configuration

This module builds and configures the LangGraph workflow for email processing.
The workflow handles email classification, information extraction, and storage.
"""

from langgraph.graph import StateGraph, END

from .state import create_initial_state
from .config import NodeNames
from .nodes import (
    new_mail_node,
    config_loader_node,
    language_detector_node,
    ai_filter_node,
    guardrail_node,
    ai_filter_guardrail_node,
    summarizer_node,
    classifier_node,
    attachment_extractor_node,
    router_node,
)

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
    graph.add_node(NodeNames.ROUTER, router_node)
    
    # Configure workflow edges
    graph.set_entry_point(NodeNames.NEW_MAIL)
    graph.add_edge(NodeNames.NEW_MAIL, NodeNames.CONFIG_LOADER)
    graph.add_edge(NodeNames.CONFIG_LOADER, NodeNames.LANGUAGE_DETECTOR)
    graph.add_edge(NodeNames.LANGUAGE_DETECTOR, NodeNames.AI_FILTER)
    graph.add_edge(NodeNames.AI_FILTER, NodeNames.GUARDRAIL)
    
    # Conditional edge from guardrail: continue if safe, end if dangerous
    def should_continue_after_guardrail(state):
        """Check if workflow should continue after guardrail."""
        if "dangerous_email" in state:
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
    
    # Edge from summarizer to classifier
    graph.add_edge(NodeNames.SUMMARIZER, NodeNames.CLASSIFIER)
    
    # Conditional edge from classifier: check confidence and attachments
    def should_continue_after_classifier(state):
        """Check if workflow should continue after classifier and route based on attachments."""
        if "low_confidence_classification" in state:
            return END
        
        # Check if there are attachments to process
        attachments = state.get("attachments", [])
        if attachments and len(attachments) > 0:
            return NodeNames.ATTACHMENT_EXTRACTOR
        else:
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
    
    # Edge from attachment extractor to router
    graph.add_edge(NodeNames.ATTACHMENT_EXTRACTOR, NodeNames.ROUTER)
    
    # Router ends the workflow (extraction nodes not implemented yet)
    graph.add_edge(NodeNames.ROUTER, END)
    
    return graph


# Create the graph instance
graph = create_email_classification_graph()


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
                "user_config": None
            }
        else:
            initial_state = create_initial_state()
        
        print(f"🎯 [WORKFLOW] Starting with initial state:")
        print(f"   📧 Body: {initial_state.get('email_body', 'None')[:100]}...")
        print(f"   📎 Attachments: {len(initial_state.get('attachments', []))}")
        print(f"   🏷️ Category: {initial_state.get('category')}")
        print(f"   🧵 Thread ID: {initial_state.get('extracted_info', {}).get('thread_id')}")
        
        # Compile and execute the workflow
        compiled_graph = graph.compile()
        result = compiled_graph.invoke(initial_state)
        
        # Check if dangerous email was detected
        if "dangerous_email" in result:
            print(f"🚨 [WORKFLOW] DANGEROUS EMAIL DETECTED!")
            return result["dangerous_email"]
        
        # Check if low confidence classification was detected
        if "low_confidence_classification" in result:
            print(f"⚠️ [WORKFLOW] LOW CONFIDENCE CLASSIFICATION DETECTED!")
            return result["low_confidence_classification"]
        
        print(f"🏁 [WORKFLOW] Completed with result: {result}")
        return result
        
    except Exception as e:
        print(f"❌ [WORKFLOW] Error executing workflow: {e}")
        return {"error": str(e), "status": "failed"}


if __name__ == "__main__":
    run_workflow()
