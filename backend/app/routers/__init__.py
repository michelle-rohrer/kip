"""API routers package."""

from app.routers.auth import router as auth_router
from app.routers.cycle import router as cycle_router
from app.routers.injury import router as injury_router
from app.routers.privacy import router as privacy_router
from app.routers.training import router as training_router
from app.routers.wellness import router as wellness_router

__all__ = [
    "auth_router",
    "cycle_router",
    "injury_router",
    "privacy_router",
    "training_router",
    "wellness_router",
]
