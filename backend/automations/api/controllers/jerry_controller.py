"""Controller for Jerry chatbot API endpoints."""
from typing import Optional, Dict, Any, List
from automations.api.services.jerry_service import get_jerry_service
from automations.api.handler_exception import (
    JerryInternalException,
    JerryMessageRequiredException,
    JerryThreadIdRequiredException,
    JerryThreadNotFoundException,
    JerryToolNameRequiredException,
    JerryToolParamsRequiredException,
    JerryUserIdRequiredException,
)


class JerryController:
    """Controller that handles Jerry chatbot HTTP requests and responses."""
    
    def __init__(self):
        """Initialize the controller with Jerry service."""
        self.service = get_jerry_service()
    
    def create_thread(self, user_id: str) -> Dict[str, Any]:
        """
        Create a new conversation thread.
        
        Args:
            user_id: The user identifier
            
        Returns:
            Dictionary with thread_id
        """
        if not user_id:
            raise JerryUserIdRequiredException()
        
        try:
            thread_id = self.service.create_thread(user_id)
            return {
                "thread_id": thread_id,
                "message": "Thread created successfully"
            }
        except Exception as e:
            raise JerryInternalException("Error creating thread", e)
    
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
            thread_id: Optional thread identifier
            
        Returns:
            Dictionary with thread_id and response
        """
        if not user_id:
            raise JerryUserIdRequiredException()
        
        if not message:
            raise JerryMessageRequiredException()
        
        try:
            result = self.service.send_message(user_id, message, thread_id)
            return result
        except Exception as e:
            raise JerryInternalException("Error sending message", e)
    
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
            thread_id: Optional thread identifier
            
        Yields:
            Chunks of the response
        """
        if not user_id:
            raise JerryUserIdRequiredException()
        
        if not message:
            raise JerryMessageRequiredException()
        
        try:
            for chunk in self.service.stream_message(user_id, message, thread_id):
                yield chunk
        except Exception as e:
            raise JerryInternalException("Error streaming message", e)
    
    def get_thread_history(self, thread_id: str) -> Dict[str, Any]:
        """
        Retrieve conversation history for a thread.
        
        Args:
            thread_id: The thread identifier
            
        Returns:
            Dictionary with messages list
        """
        if not thread_id:
            raise JerryThreadIdRequiredException()
        
        try:
            history = self.service.get_thread_history(thread_id)
            return {
                "thread_id": thread_id,
                "messages": history,
                "count": len(history)
            }
        except Exception as e:
            raise JerryInternalException("Error retrieving thread history", e)
    
    def delete_thread(self, thread_id: str) -> Dict[str, Any]:
        """
        Delete a conversation thread.
        
        Args:
            thread_id: The thread identifier
            
        Returns:
            Success message
        """
        if not thread_id:
            raise JerryThreadIdRequiredException()
        
        try:
            success = self.service.delete_thread(thread_id)
            if success:
                return {
                    "message": "Thread deleted successfully",
                    "thread_id": thread_id
                }
            else:
                raise JerryThreadNotFoundException()
        except Exception as e:
            raise JerryInternalException("Error deleting thread", e)
    
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
            thread_id: Optional thread identifier
            user_id: Optional user identifier
            
        Returns:
            Result of the tool execution
        """
        if not tool_name:
            raise JerryToolNameRequiredException()
        
        if not tool_params:
            raise JerryToolParamsRequiredException()
        
        try:
            result = self.service.execute_tool(
                tool_name, 
                tool_params, 
                thread_id, 
                user_id
            )
            return result
        except Exception as e:
            raise JerryInternalException("Error executing tool", e)
    
    def get_available_tools(self) -> Dict[str, Any]:
        """
        Get list of available tools.
        
        Returns:
            Dictionary with tools list
        """
        try:
            tools = self.service.get_available_tools()
            return {
                "tools": tools,
                "count": len(tools)
            }
        except Exception as e:
            raise JerryInternalException("Error retrieving tools", e)
