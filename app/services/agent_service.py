"""Agent CRUD business logic."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import MCCError
from app.db.models import Agent, Project
from app.models.agent import AgentCreate, AgentUpdate


async def list_agents(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> list[Agent]:
    await _get_project_or_404(db, project_id)
    result = await db.execute(
        select(Agent).where(Agent.project_id == project_id).order_by(Agent.created_at)
    )
    return list(result.scalars().all())


async def get_agent(
    db: AsyncSession,
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> Agent:
    await _get_project_or_404(db, project_id)
    agent = await db.get(Agent, agent_id)
    if not agent or agent.project_id != project_id:
        raise MCCError(code="AGENT_NOT_FOUND", message="Agent not found", status_code=404)
    return agent


async def create_agent(
    db: AsyncSession,
    project_id: uuid.UUID,
    data: AgentCreate,
) -> Agent:
    await _get_project_or_404(db, project_id)
    valid_types = {"orchestrator", "architect", "coder", "tester", "reviewer"}
    if data.type not in valid_types:
        raise MCCError(
            code="INVALID_AGENT_TYPE",
            message=f"Agent type must be one of: {', '.join(sorted(valid_types))}",
            status_code=400,
        )
    agent = Agent(
        name=data.name,
        type=data.type,
        model_config_json=data.model_config_json,
        system_prompt=data.system_prompt,
        rules_file_path=data.rules_file_path,
        project_id=project_id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def update_agent(
    db: AsyncSession,
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
    data: AgentUpdate,
) -> Agent:
    agent = await get_agent(db, project_id, agent_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)
    await db.commit()
    await db.refresh(agent)
    return agent


async def reset_agent(
    db: AsyncSession,
    project_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> Agent:
    """Reset agent to default state (clear custom prompt, set active, clear memories)."""
    from app.services.memory_service import delete_agent_memories

    agent = await get_agent(db, project_id, agent_id)
    agent.system_prompt = None
    agent.is_active = True
    await delete_agent_memories(db, agent_id)
    await db.commit()
    await db.refresh(agent)
    return agent


async def _get_project_or_404(db: AsyncSession, project_id: uuid.UUID) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise MCCError(code="PROJECT_NOT_FOUND", message="Project not found", status_code=404)
    return project
