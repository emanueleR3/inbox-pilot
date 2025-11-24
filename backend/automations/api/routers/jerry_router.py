from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import json
from automations.api.controllers.jerry_controller import JerryController

router = APIRouter(tags=["jerry"])
controller = JerryController()

#TODO: API to retrieve all threads for a user

class CreateThreadRequest(BaseModel):
    """Request model for creating a new thread."""
    user_id: str = Field(..., description="User identifier")


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., description="Message text")
    thread_id: Optional[str] = Field(None, description="Thread identifier (creates new if omitted)")


class StreamMessageRequest(BaseModel):
    """Request model for streaming a message."""
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., description="Message text")
    thread_id: Optional[str] = Field(None, description="Thread identifier (creates new if omitted)")


class ExecuteToolRequest(BaseModel):
    """Request model for executing a tool."""
    tool_name: str = Field(..., description="Name of the tool to execute")
    tool_params: Dict[str, Any] = Field(..., description="Parameters for the tool")
    thread_id: Optional[str] = Field(None, description="Optional thread identifier")
    user_id: Optional[str] = Field(None, description="Optional user identifier")


@router.post("/thread/create")
async def create_thread(request: CreateThreadRequest):
    """
    Create a new conversation thread.
    
    Args:
        request: CreateThreadRequest with user_id
        
    Returns:
        Dictionary with thread_id
    """
    return controller.create_thread(request.user_id)


@router.post("/message")
async def send_message(request: SendMessageRequest):
    """
    Send a message to Jerry and receive a response.
    
    Args:
        request: SendMessageRequest with user_id, message, and optional thread_id
        
    Returns:
        Dictionary with thread_id and response
    """
    return controller.send_message(
        request.user_id,
        request.message,
        request.thread_id
    )


@router.post("/message/stream")
async def stream_message(request: StreamMessageRequest):
    """
    Send a message to Jerry and stream the response.
    
    Args:
        request: StreamMessageRequest with user_id, message, and optional thread_id
        
    Returns:
        StreamingResponse with Server-Sent Events
    """
    async def event_generator():
        try:
            for chunk in controller.stream_message(
                request.user_id,
                request.message,
                request.thread_id
            ):
                # Send as Server-Sent Events
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            error_data = {"error": str(e), "type": "error"}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/thread/{thread_id}/history")
async def get_thread_history(thread_id: str):
    """
    Retrieve conversation history for a thread.
    
    Args:
        thread_id: The thread identifier
        
    Returns:
        Dictionary with messages list
    """
    return controller.get_thread_history(thread_id)


@router.delete("/thread/{thread_id}")
async def delete_thread(thread_id: str):
    """
    Delete/reset a conversation thread.
    
    Args:
        thread_id: The thread identifier
        
    Returns:
        Success message
    """
    return controller.delete_thread(thread_id)


@router.post("/tool/execute")
async def execute_tool(request: ExecuteToolRequest):
    """
    Execute a specific tool directly without going through the agent.
    
    Args:
        request: ExecuteToolRequest with tool_name, tool_params, and optional thread_id/user_id
        
    Returns:
        Result of the tool execution
    """
    return controller.execute_tool(
        request.tool_name,
        request.tool_params,
        request.thread_id,
        request.user_id
    )


@router.get("/tools")
async def get_available_tools():
    """
    Get list of available tools that can be executed.
    
    Returns:
        Dictionary with tools list and descriptions
    """
    return controller.get_available_tools()
