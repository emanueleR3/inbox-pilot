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
        #print(f"🧵 Thread ID: {payload.thread_id}")
        #print(f"📨 From: {payload.from_}")
        #print(f"📬 Box: {payload.box_email}")
        #print(f"📎 Attachments: {len(payload.attachment_ids)}")
        #print(f"🏷️ Category: {payload.category}")
        #print(f"🏷️ Subcategory: {payload.subcategory}")
        
        # Convert payload to dict for workflow
        email_data = {
            "thread_id": payload.thread_id,
            "message_id": payload.message_id,
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
            "no_reply": payload.no_reply
        }
        
        # Execute the email classification workflow
        print(f"🚀 [WORKFLOW] Starting email classification workflow...")
        workflow_result = run_workflow(email_data)
        print(f"✅ [WORKFLOW] Workflow completed: {workflow_result}")
        
        return WorkflowResponse(
            status="processed",
            thread_id=payload.thread_id,
            action_taken="workflow_executed",
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
