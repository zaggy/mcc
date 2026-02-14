"""Dispatch target resolution for conversation messages."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.mention import parse_mentions, resolve_mentioned_agents
from app.db.models import Agent, ConversationParticipant


async def resolve_dispatch_targets(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    message_content: str,
) -> list[uuid.UUID]:
    """Determine which agents should receive a message.

    1. Parse @mentions from the message content.
    2. Load conversation participants with agent name/type.
    3. Resolve mentions to agent IDs.
    4. If no mentions resolve, fall back to ALL participants.
    """
    # Load participants joined with Agent for name/type
    result = await db.execute(
        select(
            ConversationParticipant.agent_id,
            Agent.name,
            Agent.type,
        )
        .join(Agent, ConversationParticipant.agent_id == Agent.id)
        .where(
            ConversationParticipant.conversation_id == conversation_id,
            Agent.is_active.is_(True),
        )
    )
    rows = result.all()

    if not rows:
        return []

    all_agent_ids = [row.agent_id for row in rows]
    participants = [{"agent_id": row.agent_id, "name": row.name, "type": row.type} for row in rows]

    # Parse and resolve mentions
    mentions = parse_mentions(message_content)
    if mentions:
        resolved = resolve_mentioned_agents(mentions, participants)
        if resolved:
            return resolved

    # No mentions or none resolved → dispatch to all
    return all_agent_ids
