"""Controller for Jerry chatbot API endpoints - proxies requests to automations service."""

from fastapi import HTTPException, status
from typing import Optional, Dict, Any
from src.modules.jerry.src.utils.utils import forward_post, forward_get, forward_delete


class JerryController:
    """Controller that proxies Jerry chatbot HTTP requests to the automations service."""
    
    async def create_thread(self, user_id: str) -> Dict[str, Any]:
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
        
        payload = {"user_id": user_id}
        return await forward_post("/thread/create", payload)
    
    async def send_message(
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
        
        payload = {
            "user_id": user_id,
            "message": message
        }
        if thread_id:
            payload["thread_id"] = thread_id
        
        return await forward_post("/message", payload)
    
    async def get_thread_history(self, thread_id: str) -> Dict[str, Any]:
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
        
        return await forward_get(f"/thread/{thread_id}/history")
    
    async def delete_thread(self, thread_id: str) -> Dict[str, Any]:
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
        
        return await forward_delete(f"/thread/{thread_id}")
    
    async def execute_tool(
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
        
        payload = {
            "tool_name": tool_name,
            "tool_params": tool_params
        }
        if thread_id:
            payload["thread_id"] = thread_id
        if user_id:
            payload["user_id"] = user_id
        
        return await forward_post("/tool/execute", payload)
    
    async def get_available_tools(self) -> Dict[str, Any]:
        """
        Get list of available tools.
        
        Returns:
            Dictionary with tools list
        """
        return await forward_get("/tools")
