from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional
from datetime import datetime

router = APIRouter(tags=["agents-emails"])

@router.get("/")
async def get_email_agents():
    """
    Get list of available email agents
    """
    return {
        "not implemented": "Email agents - to be implemented"
    }