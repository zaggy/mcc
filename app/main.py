import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.exceptions import MCCError, mcc_exception_handler
from app.db.session import async_session


async def _auto_seed() -> None:
    """Seed database on first startup if no admin user exists."""
    from app.db.seed import seed_database

    async with async_session() as session:
        await seed_database(session)


@asynccontextmanager
async def lifespan(application: FastAPI):
    from app.services.openrouter import OpenRouterClient

    await _auto_seed()
    client = OpenRouterClient()
    application.state.openrouter = client
    yield
    await client.close()


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app = FastAPI(
    title="Mission Control Center",
    description="Multi-agent AI software development platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(MCCError, mcc_exception_handler)  # type: ignore[arg-type]

app.include_router(api_router)

# Mount Socket.io at /ws
from app.api.websocket import sio_app  # noqa: E402

app.mount("/ws", sio_app)
