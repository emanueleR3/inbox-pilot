"""FastAPI routes for Jerry chatbot - proxies to automations service."""

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from src.modules.jerry.src.controllers.jerry_controller import JerryController
from src.modules.jerry.src.utils.utils import forward_stream

router = APIRouter(tags=["jerry"])
controller = JerryController()


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


@router.post(
    "/thread/create",
    summary="Create a new conversation thread",
    description="Creates a new conversation thread for a user.",
    responses={
        200: {
            "description": "Thread created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "thread_id": "thread_abc123",
                        "message": "Thread created successfully"
                    }
                }
            }
        },
        400: {"description": "Invalid request - user_id is required"},
        500: {"description": "Internal server error"}
    }
)
async def create_thread(request: CreateThreadRequest):
    """
    Create a new conversation thread.
    
    Args:
        request: CreateThreadRequest with user_id
        
    Returns:
        Dictionary with thread_id
    """
    return await controller.create_thread(request.user_id)


@router.post(
    "/message",
    summary="Send a message to Jerry",
    description="Send a message to Jerry and receive a response. Creates a new thread if thread_id is not provided.",
    responses={
        200: {
            "description": "Message sent successfully",
            "content": {
                "application/json": {
                    "example": {
                        "thread_id": "thread_abc123",
                        "response": "Hello! How can I help you today?"
                    }
                }
            }
        },
        400: {"description": "Invalid request - user_id and message are required"},
        500: {"description": "Internal server error"}
    }
)
async def send_message(request: SendMessageRequest):
    """
    Send a message to Jerry and receive a response.
    
    Args:
        request: SendMessageRequest with user_id, message, and optional thread_id
        
    Returns:
        Dictionary with thread_id and response
    """
    return await controller.send_message(
        request.user_id,
        request.message,
        request.thread_id
    )


@router.post(
    "/message/stream",
    summary="Stream a message response from Jerry",
    description="Send a message to Jerry and stream the response in real-time using Server-Sent Events.",
    responses={
        200: {
            "description": "Streaming response",
            "content": {
                "text/event-stream": {
                    "example": "data: {\"type\": \"token\", \"content\": \"Hello\"}\n\n"
                }
            }
        },
        400: {"description": "Invalid request - user_id and message are required"},
        500: {"description": "Internal server error"}
    }
)
async def stream_message(request: StreamMessageRequest):
    """
    Send a message to Jerry and stream the response.
    
    Args:
        request: StreamMessageRequest with user_id, message, and optional thread_id
        
    Returns:
        StreamingResponse with Server-Sent Events
    """
    payload = {
        "user_id": request.user_id,
        "message": request.message
    }
    if request.thread_id:
        payload["thread_id"] = request.thread_id
    
    return StreamingResponse(
        forward_stream("/message/stream", payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get(
    "/thread/{thread_id}/history",
    summary="Get thread conversation history",
    description="Retrieve the full conversation history for a specific thread.",
    responses={
        200: {
            "description": "Thread history retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "thread_id": "thread_abc123",
                        "messages": [
                            {"role": "user", "content": "Hello"},
                            {"role": "assistant", "content": "Hi! How can I help?"}
                        ],
                        "count": 2
                    }
                }
            }
        },
        400: {"description": "Invalid request - thread_id is required"},
        404: {"description": "Thread not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_thread_history(thread_id: str):
    """
    Retrieve conversation history for a thread.
    
    Args:
        thread_id: The thread identifier
        
    Returns:
        Dictionary with messages list
    """
    return await controller.get_thread_history(thread_id)


@router.delete(
    "/thread/{thread_id}",
    summary="Delete a conversation thread",
    description="Delete/reset a conversation thread and all its messages.",
    responses={
        200: {
            "description": "Thread deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Thread deleted successfully",
                        "thread_id": "thread_abc123"
                    }
                }
            }
        },
        400: {"description": "Invalid request - thread_id is required"},
        404: {"description": "Thread not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_thread(thread_id: str):
    """
    Delete/reset a conversation thread.
    
    Args:
        thread_id: The thread identifier
        
    Returns:
        Success message
    """
    return await controller.delete_thread(thread_id)


@router.post(
    "/tool/execute",
    summary="Execute a tool directly",
    description="Execute a specific tool without going through the conversational agent.",
    responses={
        200: {
            "description": "Tool executed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "result": "Tool execution result",
                        "tool_name": "calendar_tool"
                    }
                }
            }
        },
        400: {"description": "Invalid request - tool_name and tool_params are required"},
        500: {"description": "Internal server error"}
    }
)
async def execute_tool(request: ExecuteToolRequest):
    """
    Execute a specific tool directly without going through the agent.
    
    Args:
        request: ExecuteToolRequest with tool_name, tool_params, and optional thread_id/user_id
        
    Returns:
        Result of the tool execution
    """
    return await controller.execute_tool(
        request.tool_name,
        request.tool_params,
        request.thread_id,
        request.user_id
    )


@router.get(
    "/tools",
    summary="Get available tools",
    description="Retrieve a list of all available tools that can be executed.",
    responses={
        200: {
            "description": "Tools list retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "tools": [
                            {
                                "name": "calendar_tool",
                                "description": "Manages calendar events"
                            },
                            {
                                "name": "email_tool",
                                "description": "Handles email operations"
                            }
                        ],
                        "count": 2
                    }
                }
            }
        },
        500: {"description": "Internal server error"}
    }
)
async def get_available_tools():
    """
    Get list of available tools that can be executed.
    
    Returns:
        Dictionary with tools list and descriptions
    """
    return await controller.get_available_tools()
