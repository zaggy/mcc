"""Conversation and message business logic with cursor-based pagination."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import MCCError
from app.db.models import Conversation, ConversationParticipant, Message, Project
from app.models.conversation import ConversationCreate, ConversationUpdate


async def list_conversations(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> list[Conversation]:
    await _get_project_or_404(db, project_id)
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation(
    db: AsyncSession,
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> Conversation:
    await _get_project_or_404(db, project_id)
    conv = await db.get(Conversation, conversation_id)
    if not conv or conv.project_id != project_id:
        raise MCCError(
            code="CONVERSATION_NOT_FOUND",
            message="Conversation not found",
            status_code=404,
        )
    return conv


async def create_conversation(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ConversationCreate,
) -> Conversation:
    await _get_project_or_404(db, project_id)
    valid_types = {"issue", "general", "task", "review"}
    if data.type not in valid_types:
        raise MCCError(
            code="INVALID_CONVERSATION_TYPE",
            message=f"Conversation type must be one of: {', '.join(sorted(valid_types))}",
            status_code=400,
        )
    conv = Conversation(
        title=data.title,
        type=data.type,
        project_id=project_id,
        created_by_user_id=user_id,
    )
    db.add(conv)
    await db.flush()

    # Add agent participants
    for agent_id in data.agent_ids:
        participant = ConversationParticipant(
            conversation_id=conv.id,
            agent_id=agent_id,
        )
        db.add(participant)

    await db.commit()
    await db.refresh(conv)
    return conv


async def update_conversation(
    db: AsyncSession,
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    data: ConversationUpdate,
) -> Conversation:
    conv = await get_conversation(db, project_id, conversation_id)
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data:
        valid_statuses = {"active", "paused", "completed", "archived"}
        if update_data["status"] not in valid_statuses:
            raise MCCError(
                code="INVALID_STATUS",
                message=f"Status must be one of: {', '.join(sorted(valid_statuses))}",
                status_code=400,
            )
    for key, value in update_data.items():
        setattr(conv, key, value)
    await db.commit()
    await db.refresh(conv)
    return conv


async def get_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    before: uuid.UUID | None = None,
    limit: int = 50,
) -> tuple[list[Message], bool]:
    """Cursor-based pagination for messages.

    Returns (messages, has_more). Messages ordered newest-first.
    """
    query = select(Message).where(Message.conversation_id == conversation_id)

    if before:
        # Get the created_at of the cursor message
        cursor_msg = await db.get(Message, before)
        if cursor_msg:
            query = query.where(Message.created_at < cursor_msg.created_at)

    query = query.order_by(Message.created_at.desc()).limit(limit + 1)
    result = await db.execute(query)
    rows = list(result.scalars().all())

    has_more = len(rows) > limit
    messages = rows[:limit]
    # Return in chronological order
    messages.reverse()
    return messages, has_more


async def create_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
) -> Message:
    """Save a user message to the conversation."""
    msg = Message(
        conversation_id=conversation_id,
        author_type="user",
        user_id=user_id,
        content=content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_conversation_agent_ids(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> list[uuid.UUID]:
    """Get all active agent participant IDs for a conversation."""
    result = await db.execute(
        select(ConversationParticipant.agent_id).where(
            ConversationParticipant.conversation_id == conversation_id
        )
    )
    return list(result.scalars().all())


async def _get_project_or_404(db: AsyncSession, project_id: uuid.UUID) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise MCCError(code="PROJECT_NOT_FOUND", message="Project not found", status_code=404)
    return project
