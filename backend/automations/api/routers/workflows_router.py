from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from ec_system.graph.graph import run_workflow

router = APIRouter(tags=["workflows"])


class EmailWorkflowPayload(BaseModel):
    """Email workflow payload received from broker"""
    thread_id: str = Field(..., description="Thread UUID from database")
    message_id: str = Field(..., description="Email message ID")
    email_id: Optional[str] = Field(None, description="Email UUID from emails table")
    microsoft_message_id: Optional[str] = Field(None, description="Microsoft Graph internal message ID for replies")
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
    action: Optional[str] = Field(None, description="Action type from broker (thread_created, send_to_summarizer, etc.)")
    summarizer_only: bool = Field(default=False, description="Whether to only run summarizer without full workflow")
    original_thread_id: Optional[str] = Field(None, description="Original thread ID from email provider (e.g., Gmail thread ID)")

    class Config:
        populate_by_name = True


class WorkflowResponse(BaseModel):
    """Response from workflow processing"""
    status: str = Field(..., description="Processing status")
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
        print(f"📧 [NEW WORKFLOW] Received email workflow request")
        # Convert payload to dict for workflow
        email_data = {
            "thread_id": payload.thread_id,
            "message_id": payload.message_id,
            "email_id": payload.email_id,
            "microsoft_message_id": payload.microsoft_message_id,
            "reply_to_id": payload.reply_to_id,
            "box_email": payload.box_email,
            "from": payload.from_,
            "to": payload.to,
            "cc": payload.cc,
            "subject": payload.subject,
            "subcategory": payload.subcategory,
            "category": payload.category,
            "body": payload.body,
            "provider": payload.provider,
            "attachment_ids": payload.attachment_ids,
            "has_attachments": payload.has_attachments,
            "extended_summary": payload.extended_summary,
            "no_reply": payload.no_reply,
            "action": payload.action,
            "summarizer_only": payload.summarizer_only,
            "original_thread_id": payload.original_thread_id
        }
        
        # Execute the email classification workflow
        run_workflow(email_data)
        
        return WorkflowResponse(
            status="processed",
            message="Email workflow processed successfully"
        )
        
    except Exception as e:
        print(f"❌ [WORKFLOW] Error processing email workflow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process email workflow: {str(e)}"
        )


@router.post("/test")
async def test_endpoint(data: dict):
    """Test endpoint per verificare che arrivi il payload"""
    print(f"🧪 [TEST] Received test data: {data}")
    return {"status": "test_ok", "received": data}

@router.get("/health")
async def workflows_health():
    """Health check endpoint for workflows module"""
    return {
        "status": "healthy",
        "module": "workflows",
        "version": "1.0.0"
    }
