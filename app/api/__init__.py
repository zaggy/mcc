from fastapi import APIRouter

from app.api.agent_memory import router as agent_memory_router
from app.api.agents import router as agents_router
from app.api.auth import router as auth_router
from app.api.conversations import router as conversations_router
from app.api.health import router as health_router
from app.api.issues import router as issues_router
from app.api.projects import router as projects_router
from app.api.pull_requests import router as pull_requests_router
from app.api.webhooks import router as webhooks_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(agents_router)
api_router.include_router(conversations_router)
api_router.include_router(agent_memory_router)
api_router.include_router(issues_router)
api_router.include_router(pull_requests_router)
api_router.include_router(webhooks_router)
