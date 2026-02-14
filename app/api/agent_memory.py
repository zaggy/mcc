"""Agent memory REST endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import MCCError
from app.db.models import User
from app.db.session import get_db
from app.models.memory import MemoryCreate, MemoryRead, MemoryUpdate
from app.services import memory_service

router = APIRouter(
    prefix="/projects/{project_id}/agents/{agent_id}/memory",
    tags=["agent-memory"],
)


@router.get("", response_model=list[MemoryRead])
async def list_memories(
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
    category: str | None = Query(None),
    min_importance: int = Query(1, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await memory_service.get_memories(
        db,
        agent_id,
        project_id=project_id,
        category=category,
        min_importance=min_importance,
    )


@router.post("", response_model=MemoryRead, status_code=201)
async def create_memory(
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
    data: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    memory = await memory_service.store_memory(db, agent_id, project_id, data)
    await db.commit()
    await db.refresh(memory)
    return memory


@router.get("/{memory_id}", response_model=MemoryRead)
async def get_memory(
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
    memory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    memory = await memory_service.get_memory(db, memory_id)
    if not memory or memory.agent_id != agent_id:
        raise MCCError(code="MEMORY_NOT_FOUND", message="Memory not found", status_code=404)
    return memory


@router.patch("/{memory_id}", response_model=MemoryRead)
async def update_memory(
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
    memory_id: uuid.UUID,
    data: MemoryUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # Verify the memory belongs to this agent
    existing = await memory_service.get_memory(db, memory_id)
    if not existing or existing.agent_id != agent_id:
        raise MCCError(code="MEMORY_NOT_FOUND", message="Memory not found", status_code=404)

    memory = await memory_service.update_memory(db, memory_id, data)
    await db.commit()
    await db.refresh(memory)
    return memory


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
    memory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # Verify the memory belongs to this agent
    existing = await memory_service.get_memory(db, memory_id)
    if not existing or existing.agent_id != agent_id:
        raise MCCError(code="MEMORY_NOT_FOUND", message="Memory not found", status_code=404)

    await memory_service.delete_memory(db, memory_id)
    await db.commit()
