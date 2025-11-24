"""Controller for Jerry chatbot API endpoints."""

from fastapi import HTTPException, status
from typing import Optional, Dict, Any, List
from automations.api.services.jerry_service import get_jerry_service


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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required"
            )
        
        try:
            thread_id = self.service.create_thread(user_id)
            return {
                "thread_id": thread_id,
                "message": "Thread created successfully"
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating thread: {str(e)}"
            )
    
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required"
            )
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="message is required"
            )
        
        try:
            result = self.service.send_message(user_id, message, thread_id)
            return result
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error sending message: {str(e)}"
            )
    
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required"
            )
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="message is required"
            )
        
        try:
            for chunk in self.service.stream_message(user_id, message, thread_id):
                yield chunk
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error streaming message: {str(e)}"
            )
    
    def get_thread_history(self, thread_id: str) -> Dict[str, Any]:
        """
        Retrieve conversation history for a thread.
        
        Args:
            thread_id: The thread identifier
            
        Returns:
            Dictionary with messages list
        """
        if not thread_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="thread_id is required"
            )
        
        try:
            history = self.service.get_thread_history(thread_id)
            return {
                "thread_id": thread_id,
                "messages": history,
                "count": len(history)
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving thread history: {str(e)}"
            )
    
    def delete_thread(self, thread_id: str) -> Dict[str, Any]:
        """
        Delete a conversation thread.
        
        Args:
            thread_id: The thread identifier
            
        Returns:
            Success message
        """
        if not thread_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="thread_id is required"
            )
        
        try:
            success = self.service.delete_thread(thread_id)
            if success:
                return {
                    "message": "Thread deleted successfully",
                    "thread_id": thread_id
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Thread not found or could not be deleted"
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting thread: {str(e)}"
            )
    
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tool_name is required"
            )
        
        if not tool_params:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tool_params is required"
            )
        
        try:
            result = self.service.execute_tool(
                tool_name, 
                tool_params, 
                thread_id, 
                user_id
            )
            return result
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error executing tool: {str(e)}"
            )
    
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving tools: {str(e)}"
            )
