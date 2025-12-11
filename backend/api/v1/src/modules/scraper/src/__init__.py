"""Scraper module source."""
from .routes import router
from .controllers import ScraperController

__all__ = ["router", "ScraperController"]
