"""
Pydantic models for LLM structured outputs in the quiz system.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class BulletListItem(BaseModel):
    """Single item in the bullet list."""
    name: str = Field(description="Category name")
    completed: bool = Field(default=False, description="Completed or skipped")


class ValidationResponse(BaseModel):
    """Response from the validation node."""
    is_valid: bool = Field(description="True if business info is clear enough")
    missing_info: Optional[str] = Field(default=None, description="What's missing (if invalid)")
    clarification_request: Optional[str] = Field(default=None, description="Request for more info (if invalid)")
    business_summary: Optional[str] = Field(default=None, description="Business summary (if valid)")


class PlanResponse(BaseModel):
    """Response from the planning node."""
    bullet_list: List[BulletListItem] = Field(description="Categories to collect (8-15 items)")
    answer: str = Field(description="First question to ask")


class CollectedInfoItem(BaseModel):
    """Collected info for a category."""
    category: str = Field(description="Category name")
    info: str = Field(description="Collected info (or 'SKIP' if user wants to skip)")


class NewBulletItem(BaseModel):
    """New bullet point to add."""
    name: str = Field(description="Name for the new category")
    info: Optional[str] = Field(default=None, description="Info if already provided by user")


class CollectResponse(BaseModel):
    """Response from the collect info node."""
    bullet_list: List[BulletListItem] = Field(description="Updated bullet list status")
    collected_info: List[CollectedInfoItem] = Field(description="Collected info per category")
    skipped_categories: List[str] = Field(default=[], description="Categories user wants to skip")
    items_to_add: List[NewBulletItem] = Field(default=[], description="New categories to add")
    items_to_remove: List[str] = Field(default=[], description="Categories to remove")
    needs_name_for_new_item: bool = Field(default=False, description="True if user wants to add but didn't specify name")
    answer: str = Field(default="", description="Next question or response")
    all_completed: bool = Field(default=False, description="All items done")


class ContextEditResponse(BaseModel):
    """Response for post-quiz context editing."""
    updated_markdown: str = Field(description="Updated markdown context after applying the user's request")
    answer: str = Field(description="Assistant message to the user")
    is_confirmed: bool = Field(default=False, description="True if user confirmed the context is ready to be saved")


__all__ = [
    "BulletListItem",
    "ValidationResponse",
    "PlanResponse",
    "CollectedInfoItem",
    "NewBulletItem",
    "CollectResponse",
    "ContextEditResponse",
]
