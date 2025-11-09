from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter(tags=["workflows"])


class EmailWorkflowPayload(BaseModel):
    """Email workflow payload received from broker"""
    thread_id: str = Field(..., description="Thread UUID from database")
    message_id: str = Field(..., description="Email message ID")
    reply_to_id: str = Field(default="no", description="ID of message being replied to")
    box_email: str = Field(..., description="Mailbox email receiving the message")
    from_: str = Field(..., alias="from", description="Sender email address")
    to: str = Field(..., description="Recipient email address")
    cc: Optional[str] = Field(None, description="CC email addresses")
    subject: str = Field(..., description="Email subject")
    subcategory: Optional[str] = Field(None, description="Email subcategory from database")
    category: Optional[str] = Field(None, description="Email category from database")
    body: str = Field(..., description="Cleaned email body content")
    provider: str = Field(..., description="Email provider (gmail, microsoft, imap)")
    attachment_ids: List[str] = Field(default_factory=list, description="List of attachment UUIDs")
    has_attachments: bool = Field(default=False, description="Whether email has attachments")
    extended_summary: Optional[str] = Field(None, description="Extended thread summary")
    no_reply: bool = Field(default=False, description="Whether this is a no-reply email")

    class Config:
        populate_by_name = True


class WorkflowResponse(BaseModel):
    """Response from workflow processing"""
    status: str = Field(..., description="Processing status")
    thread_id: str = Field(..., description="Thread ID that was processed")
    action_taken: Optional[str] = Field(None, description="Action taken by workflow")
    message: Optional[str] = Field(None, description="Additional information")


@router.post("/process-email", response_model=WorkflowResponse)
async def process_email_workflow(payload: EmailWorkflowPayload):
    """
    Process incoming email through automation workflows.
    Called by broker after email filtering and thread management.
    
    This endpoint orchestrates:
    - Category/subcategory classification (if not set)
    - Thread summary generation
    - AI response generation
    - Action dispatching based on category
    """
    try:
        print(f"📧 [WORKFLOW] Received email workflow request")
        print(f"🧵 Thread ID: {payload.thread_id}")
        print(f"📨 From: {payload.from_}")
        print(f"📬 Box: {payload.box_email}")
        print(f"📎 Attachments: {len(payload.attachment_ids)}")
        print(f"🏷️ Category: {payload.category}")
        print(f"🏷️ Subcategory: {payload.subcategory}")
        
        # TODO: Implement workflow orchestration
        # 1. Classify category/subcategory if not set
        # 2. Generate/update thread summary
        # 3. Determine appropriate action based on category
        # 4. Generate AI response if needed
        # 5. Dispatch to appropriate agent/workflow
        
        return WorkflowResponse(
            status="received",
            thread_id=payload.thread_id,
            action_taken="queued",
            message="Email workflow processing queued successfully"
        )
        
    except Exception as e:
        print(f"❌ [WORKFLOW] Error processing email workflow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process email workflow: {str(e)}"
        )


@router.get("/health")
async def workflows_health():
    """Health check endpoint for workflows module"""
    return {
        "status": "healthy",
        "module": "workflows",
        "version": "1.0.0"
    }
