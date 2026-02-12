"""Idempotent seed script for development data."""

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Agent, BudgetLimit, Project, User
from app.db.session import async_session, engine


async def seed_database(session: AsyncSession) -> None:
    # Check if admin already exists
    result = await session.execute(select(User).where(User.username == "admin"))
    if result.scalar_one_or_none() is not None:
        print("Seed data already exists, skipping.")
        return

    # Admin user (password will be set properly in PR #4 with argon2)
    admin = User(
        username="admin",
        email="admin@mcc.local",
        password_hash="NOT_SET_YET",
        is_admin=True,
        is_active=True,
    )
    session.add(admin)
    await session.flush()

    # Demo project
    project = Project(
        name="Demo Project",
        description="A demo project for testing MCC",
        github_repo="owner/demo-repo",
        owner_id=admin.id,
    )
    session.add(project)
    await session.flush()

    # 4 agents
    agent_configs = [
        {
            "name": "Senior Architect",
            "type": "architect",
            "model_config_json": {
                "model": "anthropic/claude-3.5-sonnet",
                "temperature": 0.2,
                "max_tokens": 4096,
            },
            "system_prompt": "You are an experienced software architect.",
        },
        {
            "name": "Coder 1",
            "type": "coder",
            "model_config_json": {
                "model": "anthropic/claude-3.5-sonnet",
                "temperature": 0.3,
                "max_tokens": 8192,
            },
            "system_prompt": "You are a skilled software developer.",
        },
        {
            "name": "QA Tester",
            "type": "tester",
            "model_config_json": {
                "model": "anthropic/claude-3.5-sonnet",
                "temperature": 0.1,
                "max_tokens": 4096,
            },
            "system_prompt": "You are a thorough QA tester.",
        },
        {
            "name": "Code Reviewer",
            "type": "reviewer",
            "model_config_json": {
                "model": "anthropic/claude-3.5-sonnet",
                "temperature": 0.1,
                "max_tokens": 4096,
            },
            "system_prompt": "You are a meticulous code reviewer.",
        },
    ]

    for config in agent_configs:
        agent = Agent(project_id=project.id, **config)
        session.add(agent)

    # Global budget limit
    budget = BudgetLimit(
        name="Global Daily Limit",
        scope_type="global",
        amount_usd=Decimal("50.00"),
        period="daily",
        alert_threshold=Decimal("0.80"),
        action_on_exceed="warn",
    )
    session.add(budget)

    await session.commit()
    print("Seed data created successfully.")


async def main() -> None:
    async with async_session() as session:
        await seed_database(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
