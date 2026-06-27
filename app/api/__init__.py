"""API routers package."""
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.tasks import router as tasks_router

__all__ = ["auth_router", "documents_router", "tasks_router"]