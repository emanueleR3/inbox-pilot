"""Centralized prompts for the Jerry chatbot system."""

JERRY_AGENT_PROMPT = """
You are Jerry, a helpful customer support chatbot that assists the customer and uses its tools to address their requests. 
Use the tools as needed to execute what the customer asks for.
"""

USER_CONTEXT_TEMPLATE = """

=== USER CONTEXT ===
The following information is about the current user and their configured services. 
Use this context to provide personalized assistance and to know which email accounts are available for sending emails.

{summary}

Configured email addresses available for sending:
{configured_emails}

=== END USER CONTEXT ===
"""


def build_enriched_prompt(user_context: dict | None) -> str:
    """
    Build the system prompt with user context.
    
    Args:
        user_context: Dictionary with user context data (summary, configured_emails)
        
    Returns:
        System prompt enriched with user context, or base prompt if no context
    """
    if not user_context:
        return JERRY_AGENT_PROMPT
    
    summary = user_context.get('summary', 'No additional context available.')
    configured_emails = user_context.get('configured_emails', [])
    emails_str = ', '.join(configured_emails) if configured_emails else 'No configured emails'
    
    context_section = USER_CONTEXT_TEMPLATE.format(
        summary=summary,
        configured_emails=emails_str
    )
    
    return JERRY_AGENT_PROMPT + context_section
