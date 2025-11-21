"""
Senders Service - Main Application
Handles webhooks for sending notification emails and response emails.
"""

import os
import logging
from fastapi import FastAPI
import uvicorn

from .routers import notification_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Senders Service",
    description="Email sending service for notifications and responses",
    version="1.0.0"
)

# Include routers
app.include_router(notification_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "senders"}


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Senders Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "notification_send": "/notification/send"
        }
    }


def main():
    """Main entry point for the senders service."""
    port = int(os.getenv("SENDERS_PORT", "8020"))
    host = os.getenv("SENDERS_HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting Senders Service on {host}:{port}")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
