"""Pydantic schemas for conversations and messages."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------
class ConversationCreate(BaseModel):
    title: str | None = None
    type: str = "general"
    agent_ids: list[uuid.UUID] = []


class ConversationRead(BaseModel):
    id: uuid.UUID
    title: str | None
    type: str
    status: str
    project_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationUpdate(BaseModel):
    title: str | None = None
    status: str | None = None


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
class MessageCreate(BaseModel):
    content: str


class MessageRead(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    author_type: str
    user_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    content: str
    tokens_in: int
    tokens_out: int
    cost_usd: Decimal
    model_used: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CursorPaginatedMessages(BaseModel):
    messages: list[MessageRead]
    has_more: bool
    next_cursor: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# Project models (additions)
# ---------------------------------------------------------------------------
class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    github_repo: str | None = None
    is_active: bool | None = None
