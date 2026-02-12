"""Agent CRUD endpoints scoped to a project."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.models.agent import AgentCreate, AgentRead, AgentUpdate
from app.services import agent_service

router = APIRouter(prefix="/projects/{project_id}/agents", tags=["agents"])


@router.get("", response_model=list[AgentRead])
async def list_agents(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await agent_service.list_agents(db, project_id)


@router.post("", response_model=AgentRead, status_code=201)
async def create_agent(
    project_id: uuid.UUID,
    data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await agent_service.create_agent(db, project_id, data)


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await agent_service.get_agent(db, project_id, agent_id)


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await agent_service.update_agent(db, project_id, agent_id, data)


@router.post("/{agent_id}/reset", response_model=AgentRead)
async def reset_agent(
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await agent_service.reset_agent(db, project_id, agent_id)
