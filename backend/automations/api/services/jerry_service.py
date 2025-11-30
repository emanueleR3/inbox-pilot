"""Service layer for Jerry chatbot system - delegates to jerry.py core logic."""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import uuid4

# Add parent directories to path to import jerry
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Import core Jerry logic and components
from automations.chatbot import jerry
from automations.chatbot.tools import send_email
from automations.chatbot.db.db import get_user_context
from automations.chatbot.prompts import JERRY_AGENT_PROMPT, build_enriched_prompt
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage


class JerryService:
    """Service to manage Jerry chatbot interactions - wraps jerry.py functionality."""
    
    def __init__(self):
        """Initialize the Jerry service using the existing jerry.py graph."""
        # Use the already initialized graph from jerry.py
        self.graph = jerry.graph
        self.checkpointer = jerry.checkpointer
        self.agent_prompt = jerry.agent_prompt
    
    def _build_system_prompt_with_context(self, user_id: str) -> str:
        """
        Build the system prompt with user context from Supabase.
        
        Args:
            user_id: The user identifier
            
        Returns:
            System prompt enriched with user context
        """
        user_context = get_user_context(user_id)
        
        if not user_context:
            print(f"⚠️ [JERRY_SERVICE] No user context found for user_id: {user_id}, using base prompt")
        else:
            print(f"✅ [JERRY_SERVICE] System prompt enriched with user context for user_id: {user_id}")
        
        return build_enriched_prompt(user_context)
    
    def create_thread(self, user_id: str) -> str:
        """
        Create a new conversation thread with user context.
        
        Args:
            user_id: The user identifier
            
        Returns:
            thread_id: The new thread identifier
        """
        thread_id = f"user{user_id}:conv{uuid4()}"
        
        # Build system prompt with user context
        system_prompt = self._build_system_prompt_with_context(user_id)
        
        # Initialize the thread with enriched system message
        config = {"configurable": {"thread_id": thread_id}}
        self.graph.invoke(
            {"messages": [SystemMessage(content=system_prompt)]},
            config=config,
        )
        
        return thread_id
    
    def send_message(
        self, 
        user_id: str, 
        message: str, 
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message to Jerry and get a response.
        Uses the handle_user_message function from jerry.py
        
        Args:
            user_id: The user identifier
            message: The message text
            thread_id: Optional thread identifier (creates new if None)
            
        Returns:
            Dictionary with thread_id and response
        """
        # Delegate to jerry.py's handle_user_message function
        result_thread_id, answer = jerry.handle_user_message(user_id, thread_id, message)
        
        return {
            "thread_id": result_thread_id,
            "response": answer.content if hasattr(answer, 'content') else str(answer),
            "message_type": answer.__class__.__name__
        }
    
    def stream_message(
        self,
        user_id: str,
        message: str,
        thread_id: Optional[str] = None
    ):
        """
        Stream a message response from Jerry.
        
        Args:
            user_id: The user identifier
            message: The message text
            thread_id: Optional thread identifier (creates new if None)
            
        Yields:
            Chunks of the response as they are generated
        """
        # Create new thread with user context if not provided
        if thread_id is None:
            thread_id = f"user{user_id}:conv{uuid4()}"
            
            # Build system prompt with user context
            system_prompt = self._build_system_prompt_with_context(user_id)
            
            # Initialize the thread with enriched system message
            config = {"configurable": {"thread_id": thread_id}}
            self.graph.invoke(
                {"messages": [SystemMessage(content=system_prompt)]},
                config=config,
            )
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # Stream the graph execution using jerry's graph
        for chunk in self.graph.stream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        ):
            # Extract relevant data from chunk
            if "chatbot" in chunk:
                messages = chunk["chatbot"].get("messages", [])
                if messages:
                    last_message = messages[-1]
                    if hasattr(last_message, 'content'):
                        yield {
                            "thread_id": thread_id,
                            "content": last_message.content,
                            "type": "message"
                        }
    
    def get_thread_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history for a thread.
        
        Args:
            thread_id: The thread identifier
            
        Returns:
            List of messages in the conversation
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            # Get the state from checkpointer using jerry's graph
            state = self.graph.get_state(config)
            
            if not state or not state.values:
                return []
            
            messages = state.values.get("messages", [])
            
            # Convert messages to serializable format
            history = []
            for msg in messages:
                if isinstance(msg, (HumanMessage, AIMessage, SystemMessage)):
                    history.append({
                        "role": self._get_role_from_message(msg),
                        "content": msg.content,
                        "type": msg.__class__.__name__
                    })
            
            return history
        except Exception as e:
            print(f"Error retrieving thread history: {str(e)}")
            return []
    
    def delete_thread(self, thread_id: str) -> bool:
        """
        Delete a conversation thread.
        
        Args:
            thread_id: The thread identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            
            # Update state to empty messages using jerry's graph
            self.graph.update_state(
                config,
                {"messages": []},
            )
            
            return True
        except Exception as e:
            print(f"Error deleting thread: {str(e)}")
            return False
    
    def execute_tool(
        self,
        tool_name: str,
        tool_params: Dict[str, Any],
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a specific tool directly.
        
        Args:
            tool_name: Name of the tool to execute
            tool_params: Parameters for the tool
            thread_id: Optional thread identifier for context
            user_id: Optional user identifier
            
        Returns:
            Result of the tool execution
        """
        try:
            # Map tool names to actual tool functions
            available_tools = {
                "send_email": send_email,
            }
            
            if tool_name not in available_tools:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found. Available tools: {list(available_tools.keys())}"
                }
            
            tool_func = available_tools[tool_name]
            
            # Execute the tool
            result = tool_func.invoke(tool_params)
            
            return {
                "success": True,
                "tool": tool_name,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools with their descriptions.
        
        Returns:
            List of tool information
        """
        #TODO Retrieve this from tools.py dynamically
        return [
            {
                "name": "send_email",
                "description": send_email.description,
                "parameters": {
                    "sender_address": "Email address of the sender",
                    "receiver_address": "Email address of the recipient",
                    "subject": "Email subject",
                    "body": "Email body content",
                    "provider": "'google' (default), 'microsoft', or 'smtp'",
                    "body_type": "'text' or 'html' (default: 'text')",
                    "cc_recipients": "List of CC email addresses (optional)",
                    "bcc_recipients": "List of BCC email addresses (optional)",
                    "attachments": "List of file paths to attach (optional)"
                }
            }
        ]
    
    @staticmethod
    def _get_role_from_message(message: BaseMessage) -> str:
        """Convert message type to role string."""
        if isinstance(message, HumanMessage):
            return "user"
        elif isinstance(message, AIMessage):
            return "assistant"
        elif isinstance(message, SystemMessage):
            return "system"
        else:
            return "unknown"


# Singleton instance
_service_instance: Optional[JerryService] = None


def get_jerry_service() -> JerryService:
    """Get or create the Jerry service singleton instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = JerryService()
    return _service_instance
