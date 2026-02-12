from fastapi import APIRouter

from app.api.agents import router as agents_router
from app.api.auth import router as auth_router
from app.api.conversations import router as conversations_router
from app.api.health import router as health_router
from app.api.projects import router as projects_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(agents_router)
api_router.include_router(conversations_router)
