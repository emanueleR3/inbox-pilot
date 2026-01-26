from typing import List, Optional

from src.core.database import get_supabase_client
from src.core.model.mailbox import (
    EmailMessage,
    EmailThreadDetail,
    EmailThreadSummary,
    FailedOutboundEmail
)


class MailboxDAO:
    def __init__(self):
        self.supabase = get_supabase_client()

    def fetch_inbox_threads(
        self,
        box_email: str,
        status: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[EmailThreadSummary]:

        query = self.supabase.table("inbox_view").select("*").eq("box_email", box_email)

        if status:
            query = query.eq("status", status)
        if category:
            query = query.eq("category", category)
        if subcategory:
            query = query.eq("subcategory", subcategory)

        rows = (
            query
            .order("last_message_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
            .data
        )

        return [
            EmailThreadSummary(
                thread_id=row["thread_id"],
                subject=row["subject"],
                category=row["category"],
                subcategory=row.get("subcategory"),
                status=row["status"],
                last_message_at=row["last_message_at"],
                last_sender_email=row["last_sender_email"],
                human_response=row["human_response"],
                summary=row.get("summary"),
                email_count=row["email_count"],
                has_attachments=row["has_attachments"],
                max_priority=row.get("max_priority")
            )
            for row in rows
        ]

    def fetch_human_review_threads(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[EmailThreadSummary]:

        rows = (
            self.supabase
            .table("inbox_human_review_view")
            .select("*")
            .order("last_message_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
            .data
        )

        return [
            EmailThreadSummary(
                thread_id=row["thread_id"],
                subject=row["subject"],
                category=row["category"],
                subcategory=row.get("subcategory"),
                status=row["status"],
                last_message_at=row["last_message_at"],
                last_sender_email=row["last_sender_email"],
                human_response=row["human_response"],
                summary=row.get("summary"),
                email_count=row["email_count"],
                has_attachments=row["has_attachments"],
                max_priority=row.get("max_priority")
            )
            for row in rows
        ]

    def fetch_thread_conversation(
        self,
        thread_id: str
    ) -> Optional[EmailThreadDetail]:

        rows = (
            self.supabase
            .table("thread_conversation_view")
            .select("*")
            .eq("thread_id", thread_id)
            .order("datetime", desc=False)
            .execute()
            .data
        )

        if not rows:
            return None

        messages = [
            EmailMessage(
                id=row["email_id"],
                subject=row.get("subject"),
                body=row.get("body"),
                direction=row["direction"],
                outcome=row.get("outcome"),
                datetime=row["datetime"],
                has_attachment=row["has_attachment"],
                ai_generated=row["ai_generated"],
                priority_score=row.get("priority_score")
            )
            for row in rows
        ]

        return EmailThreadDetail(
            thread_id=thread_id,
            subject=rows[0]["subject"],
            messages=messages,
            message_count=len(messages)
        )

    def fetch_failed_outbound_emails(self) -> List[FailedOutboundEmail]:

        rows = (
            self.supabase
            .table("failed_outbound_emails_view")
            .select("*")
            .order("datetime", desc=True)
            .execute()
            .data
        )

        return [
            FailedOutboundEmail(
                email_id=row["email_id"],
                thread_id=row.get("thread_id"),
                datetime=row["datetime"],
                outcome=row["outcome"],
                body=row.get("body")
            )
            for row in rows
        ]

    def fetch_threads_by_category(
        self,
        category: str,
        subcategory: Optional[str] = None
    ) -> List[EmailThreadSummary]:

        query = self.supabase.table("inbox_view").select("*").eq("category", category)

        if subcategory:
            query = query.eq("subcategory", subcategory)

        rows = (
            query
            .order("last_message_at", desc=True)
            .execute()
            .data
        )

        return [
            EmailThreadSummary(
                thread_id=row["thread_id"],
                subject=row["subject"],
                category=row["category"],
                subcategory=row.get("subcategory"),
                status=row["status"],
                last_message_at=row["last_message_at"],
                last_sender_email=row["last_sender_email"],
                human_response=row["human_response"],
                summary=row.get("summary"),
                email_count=row["email_count"],
                has_attachments=row["has_attachments"],
                max_priority=row.get("max_priority")
            )
            for row in rows
        ]




