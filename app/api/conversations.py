"""Conversation and message endpoints with background agent processing."""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_openrouter
from app.core.exceptions import MCCError
from app.db.models import User
from app.db.session import async_session, get_db
from app.models.conversation import (
    ConversationCreate,
    ConversationRead,
    ConversationUpdate,
    CursorPaginatedMessages,
    MessageCreate,
    MessageRead,
)
from app.services import conversation_service
from app.services.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects/{project_id}/conversations",
    tags=["conversations"],
)


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await conversation_service.list_conversations(db, project_id)


@router.post("", response_model=ConversationRead, status_code=201)
async def create_conversation(
    project_id: uuid.UUID,
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await conversation_service.create_conversation(db, project_id, user.id, data)


@router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await conversation_service.get_conversation(db, project_id, conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def update_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await conversation_service.update_conversation(db, project_id, conversation_id, data)


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
@router.get("/{conversation_id}/messages", response_model=CursorPaginatedMessages)
async def list_messages(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    before: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # Verify conversation exists and belongs to project
    await conversation_service.get_conversation(db, project_id, conversation_id)

    messages, has_more = await conversation_service.get_messages(
        db, conversation_id, before=before, limit=limit
    )
    next_cursor = messages[0].id if has_more and messages else None
    return CursorPaginatedMessages(
        messages=messages,
        has_more=has_more,
        next_cursor=next_cursor,
    )


@router.post("/{conversation_id}/messages", response_model=MessageRead, status_code=201)
async def send_message(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    data: MessageCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    openrouter: OpenRouterClient = Depends(get_openrouter),
):
    # Verify conversation is active
    conv = await conversation_service.get_conversation(db, project_id, conversation_id)
    if conv.status != "active":
        raise MCCError(
            code="CONVERSATION_NOT_ACTIVE",
            message="Cannot send messages to a non-active conversation",
            status_code=400,
        )

    # Save user message
    user_msg = await conversation_service.create_message(db, conversation_id, user.id, data.content)

    # Get participating agents and dispatch background tasks
    agent_ids = await conversation_service.get_conversation_agent_ids(db, conversation_id)
    for agent_id in agent_ids:
        background_tasks.add_task(
            _process_agent_response,
            agent_id=agent_id,
            conversation_id=conversation_id,
            openrouter=openrouter,
        )

    return user_msg


async def _process_agent_response(
    agent_id: uuid.UUID,
    conversation_id: uuid.UUID,
    openrouter: OpenRouterClient,
) -> None:
    """Background task: have an agent generate a response."""
    from app.agents.registry import create_agent
    from app.db.models import Agent

    try:
        async with async_session() as db:
            agent_record = await db.get(Agent, agent_id)
            if not agent_record or not agent_record.is_active:
                logger.warning("Agent %s not found or inactive, skipping", agent_id)
                return

            agent = create_agent(agent_record, openrouter)
            result = await agent.process_message(db, conversation_id)

            if result:
                # Emit WebSocket event if sio is available
                try:
                    from app.api.websocket import sio

                    room = str(conversation_id)
                    await sio.emit(
                        "message",
                        {
                            "id": str(result.id),
                            "conversation_id": str(conversation_id),
                            "author_type": "agent",
                            "agent_id": str(agent_id),
                            "content": result.content,
                            "created_at": result.created_at.isoformat(),
                        },
                        room=room,
                    )
                except Exception:
                    logger.debug("WebSocket emit skipped (not connected)")

    except Exception:
        logger.exception("Error processing agent %s response", agent_id)
