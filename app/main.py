from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.exceptions import MCCError, mcc_exception_handler

app = FastAPI(
    title="Mission Control Center",
    description="Multi-agent AI software development platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(MCCError, mcc_exception_handler)  # type: ignore[arg-type]

app.include_router(api_router)
