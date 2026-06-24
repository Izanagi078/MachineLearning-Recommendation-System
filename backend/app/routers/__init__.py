"""Routers package."""
from backend.app.routers.auth import router as auth_router
from backend.app.routers.movies import router as movies_router
from backend.app.routers.recommendations import router as recommendations_router
from backend.app.routers.feed import router as feed_router

__all__ = ["auth_router", "movies_router", "recommendations_router", "feed_router"]
