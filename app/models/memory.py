"""Pydantic schemas for agent memory CRUD."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    category: str
    key: str
    value: dict
    importance: int = Field(default=5, ge=1, le=10)
    expires_at: datetime | None = None


class MemoryUpdate(BaseModel):
    value: dict | None = None
    importance: int | None = Field(default=None, ge=1, le=10)
    expires_at: datetime | None = None


class MemoryRead(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    project_id: uuid.UUID | None
    category: str
    key: str
    value: dict
    importance: int
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
