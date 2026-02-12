"""Records token usage to the database and updates message cost fields."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message, TokenUsage
from app.models.openrouter import OpenRouterResponse


async def record_usage(
    db: AsyncSession,
    *,
    response: OpenRouterResponse,
    agent_id: uuid.UUID,
    agent_type: str,
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
) -> TokenUsage:
    """Create a TokenUsage row and update the associated message's cost fields."""
    now = datetime.now(UTC)
    usage = TokenUsage(
        timestamp=now,
        usage_date=now.date(),
        agent_id=agent_id,
        agent_type=agent_type,
        conversation_id=conversation_id,
        message_id=message_id,
        project_id=project_id,
        task_id=task_id,
        model=response.model,
        tokens_in=response.usage.prompt_tokens,
        tokens_out=response.usage.completion_tokens,
        cost_usd=response.cost_usd,
        request_duration_ms=response.duration_ms,
    )
    db.add(usage)

    # Update the message with cost info
    msg = await db.get(Message, message_id)
    if msg:
        msg.tokens_in = response.usage.prompt_tokens
        msg.tokens_out = response.usage.completion_tokens
        msg.cost_usd = response.cost_usd
        msg.model_used = response.model

    await db.flush()
    return usage
