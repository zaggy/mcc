"""Agent memory CRUD and context builder."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context import count_tokens
from app.db.models import AgentMemory
from app.models.memory import MemoryCreate, MemoryUpdate


async def store_memory(
    db: AsyncSession,
    agent_id: uuid.UUID,
    project_id: uuid.UUID | None,
    data: MemoryCreate,
) -> AgentMemory:
    """Create or upsert a memory entry.

    Upserts on the (agent_id, project_id, category, key) unique constraint.
    """
    # Check for existing memory with same unique key
    project_filter = (
        AgentMemory.project_id == project_id if project_id else AgentMemory.project_id.is_(None)
    )
    result = await db.execute(
        select(AgentMemory).where(
            AgentMemory.agent_id == agent_id,
            project_filter,
            AgentMemory.category == data.category,
            AgentMemory.key == data.key,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.value = data.value
        existing.importance = data.importance
        existing.expires_at = data.expires_at
        await db.flush()
        await db.refresh(existing)
        return existing

    memory = AgentMemory(
        agent_id=agent_id,
        project_id=project_id,
        category=data.category,
        key=data.key,
        value=data.value,
        importance=data.importance,
        expires_at=data.expires_at,
    )
    db.add(memory)
    await db.flush()
    await db.refresh(memory)
    return memory


async def get_memories(
    db: AsyncSession,
    agent_id: uuid.UUID,
    *,
    project_id: uuid.UUID | None = None,
    category: str | None = None,
    min_importance: int = 1,
    limit: int = 50,
) -> list[AgentMemory]:
    """Retrieve agent memories, filtering expired entries."""
    query = select(AgentMemory).where(
        AgentMemory.agent_id == agent_id,
        AgentMemory.importance >= min_importance,
    )

    if project_id is not None:
        query = query.where(AgentMemory.project_id == project_id)

    if category is not None:
        query = query.where(AgentMemory.category == category)

    # Exclude expired
    now = datetime.now(UTC)
    query = query.where((AgentMemory.expires_at.is_(None)) | (AgentMemory.expires_at > now))

    query = query.order_by(AgentMemory.importance.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_memory(
    db: AsyncSession,
    memory_id: uuid.UUID,
) -> AgentMemory | None:
    """Get a single memory by ID."""
    return await db.get(AgentMemory, memory_id)


async def update_memory(
    db: AsyncSession,
    memory_id: uuid.UUID,
    data: MemoryUpdate,
) -> AgentMemory | None:
    """Update an existing memory entry."""
    memory = await db.get(AgentMemory, memory_id)
    if not memory:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(memory, key, value)

    await db.flush()
    await db.refresh(memory)
    return memory


async def delete_memory(
    db: AsyncSession,
    memory_id: uuid.UUID,
) -> bool:
    """Delete a memory by ID. Returns True if deleted."""
    memory = await db.get(AgentMemory, memory_id)
    if not memory:
        return False
    await db.delete(memory)
    await db.flush()
    return True


async def delete_agent_memories(
    db: AsyncSession,
    agent_id: uuid.UUID,
) -> int:
    """Delete all memories for an agent. Returns count deleted."""
    result = await db.execute(delete(AgentMemory).where(AgentMemory.agent_id == agent_id))
    await db.flush()
    return result.rowcount


async def build_memory_context(
    db: AsyncSession,
    agent_id: uuid.UUID,
    project_id: uuid.UUID | None,
    max_tokens: int = 2000,
) -> str:
    """Build a text block of agent memories for injection into the system prompt.

    Fetches top memories by importance and truncates to fit max_tokens.
    """
    memories = await get_memories(db, agent_id, project_id=project_id, limit=50)
    if not memories:
        return ""

    lines: list[str] = ["## Agent Memory"]
    for mem in memories:
        line = f"- [{mem.category}] {mem.key}: {mem.value}"
        lines.append(line)

    text = "\n".join(lines)

    # Truncate if over budget
    while count_tokens(text) > max_tokens and len(lines) > 2:
        lines.pop()
        remaining = len(memories) - (len(lines) - 1)
        text = "\n".join(lines) + f"\n... ({remaining} more memories truncated)"

    return text
