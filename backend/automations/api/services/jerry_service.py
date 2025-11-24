"""Service layer for Jerry chatbot system."""

import os
from typing import Optional, List, Dict, Any
from uuid import uuid4
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph, START, END
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated
from langchain_core.runnables import RunnableConfig

# Import tools
from automations.chatbot.tools import send_email


# Agent prompt
AGENT_PROMPT = """
You are Jerry, a helpful customer support chatbot that assists the customer and uses its tools to address their requests. 
Use the tools as needed to execute what the customer asks for.
"""


class GraphState(TypedDict):
    """State schema for the chatbot graph."""
    messages: Annotated[list, add_messages]


class JerryService:
    """Service to manage Jerry chatbot interactions."""
    
    def __init__(self):
        """Initialize the Jerry service with database connection and graph."""
        supabase_project_id = os.getenv("SUPABASE_PROJECT_ID")
        supabase_password = os.getenv("SUPABASE_PASSWORD")
        
        self.db_uri = f"postgresql://postgres:{supabase_password}@db.{supabase_project_id}.supabase.co:5432/postgres?sslmode=disable"
        
        # Initialize checkpointer
        checkpointer_cm = PostgresSaver.from_conn_string(self.db_uri)
        self.checkpointer = checkpointer_cm.__enter__()
        self.checkpointer.setup()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _create_chatbot_agent(self, state: GraphState):
        """Initialize and return the chatbot agent with tools."""
        model = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0, 
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        tools = [
            send_email,
        ]
        
        agent = create_agent(model, tools=tools)
        return agent
    
    def _build_graph(self):
        """Build the LangGraph StateGraph for the chatbot."""
        builder = StateGraph(GraphState)
        builder.add_node("chatbot", self._create_chatbot_agent)
        builder.add_edge(START, "chatbot")
        builder.add_edge("chatbot", END)
        return builder.compile(checkpointer=self.checkpointer)
    
    def create_thread(self, user_id: str) -> str:
        """
        Create a new conversation thread.
        
        Args:
            user_id: The user identifier
            
        Returns:
            thread_id: The new thread identifier
        """
        thread_id = f"user{user_id}:conv{uuid4()}"
        
        # Initialize the thread with system message
        config = {"configurable": {"thread_id": thread_id}}
        self.graph.invoke(
            {"messages": [SystemMessage(content=AGENT_PROMPT)]},
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
        
        Args:
            user_id: The user identifier
            message: The message text
            thread_id: Optional thread identifier (creates new if None)
            
        Returns:
            Dictionary with thread_id and response
        """
        # Create new thread if not provided
        if thread_id is None:
            thread_id = self.create_thread(user_id)
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # Invoke the graph
        result = self.graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        
        # Extract the response
        answer = result["messages"][-1]
        
        return {
            "thread_id": thread_id,
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
        # Create new thread if not provided
        if thread_id is None:
            thread_id = self.create_thread(user_id)
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # Stream the graph execution
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
            # Get the state from checkpointer
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
            
            # Update state to empty messages
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
