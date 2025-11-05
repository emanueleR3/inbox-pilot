from fastapi import APIRouter
from .calendars import router as calendars_router
from .emails import router as emails_router

router = APIRouter(tags=["agents"])

# Include sub-routers
router.include_router(calendars_router, prefix="/calendars")
router.include_router(emails_router, prefix="/emails")

@router.get("/")
async def get_agents():
    """
    Get list of available agent types
    """
    return {
        "agents": [
            {
                "type": "calendars",
                "description": "Calendar management agents",
                "endpoint": "/agents/calendars"
            },
            {
                "type": "emails",
                "description": "Email management agents",
                "endpoint": "/agents/emails"
            }
        ]
    }
