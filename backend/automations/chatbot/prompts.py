"""Centralized prompts for the Jerry chatbot system."""

from datetime import datetime

def get_current_date_info() -> str:
    """Get formatted current date and time information."""
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y at %H:%M")

JERRY_AGENT_PROMPT_TEMPLATE = """
You are Jerry, a helpful AI assistant created by Corretto that assists users with email management and communication tasks.

=== CURRENT DATE & TIME ===
Today is {current_date}.
Use this information when the user refers to relative dates like "today", "tomorrow", "next week", "last Monday", etc.

=== GUIDELINES ===
- Always confirm important details before sending emails (recipient, subject, content)
- When searching emails, clarify the search criteria if the request is ambiguous
- For date-based queries, interpret relative dates based on the current date provided above
- Be concise but thorough in your responses
- If you encounter an error with a tool, explain it clearly to the user and suggest alternatives

Use your tools as needed to execute what the user asks for.
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

# For backwards compatibility - generate with current date
def get_jerry_agent_prompt() -> str:
    """Get the base Jerry agent prompt with current date."""
    return JERRY_AGENT_PROMPT_TEMPLATE.format(current_date=get_current_date_info())

# Static version for imports (will have the date at import time)
JERRY_AGENT_PROMPT = JERRY_AGENT_PROMPT_TEMPLATE.format(current_date=get_current_date_info())


def build_enriched_prompt(user_context: dict | None) -> str:
    """
    Build the system prompt with user context.
    
    Args:
        user_context: Dictionary with user context data (summary, configured_emails)
        
    Returns:
        System prompt enriched with user context, or base prompt if no context
    """
    # Generate base prompt with current date
    base_prompt = JERRY_AGENT_PROMPT_TEMPLATE.format(current_date=get_current_date_info())
    
    if not user_context:
        return base_prompt
    
    summary = user_context.get('summary', 'No additional context available.')
    configured_emails = user_context.get('configured_emails', [])
    emails_str = ', '.join(configured_emails) if configured_emails else 'No configured emails'
    
    context_section = USER_CONTEXT_TEMPLATE.format(
        summary=summary,
        configured_emails=emails_str
    )
    
    return base_prompt + context_section
