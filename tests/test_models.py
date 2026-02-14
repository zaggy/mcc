"""Tests for SQLAlchemy models and database operations."""

from decimal import Decimal

import psycopg2
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import (
    Agent,
    BudgetLimit,
    Conversation,
    ConversationParticipant,
    Message,
    Notification,
    Project,
    Task,
    User,
)
from app.db.session import Base

_base = settings.DATABASE_URL.rsplit("/", 1)[0]
TEST_DB_URL = f"{_base}/mcc_test"

# Ensure test DB exists (runs once at import time)
_sync_base = settings.DATABASE_URL.replace("postgresql+asyncpg://", "")
_host_part = _sync_base.rsplit("/", 1)[0]
_conn = psycopg2.connect(f"postgresql://{_host_part}/mcc")
_conn.autocommit = True
_cur = _conn.cursor()
_cur.execute("SELECT 1 FROM pg_database WHERE datname = 'mcc_test'")
if not _cur.fetchone():
    _cur.execute("CREATE DATABASE mcc_test")
_cur.close()
_conn.close()


@pytest.fixture
async def db():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _create_user(db: AsyncSession, username: str = "testuser") -> User:
    user = User(
        username=username,
        email=f"{username}@test.com",
        password_hash="fakehash",
    )
    db.add(user)
    await db.flush()
    return user


async def _create_project(db: AsyncSession, user: User) -> Project:
    project = Project(
        name="Test Project",
        github_repo="test/repo",
        owner_id=user.id,
    )
    db.add(project)
    await db.flush()
    return project


async def test_create_user(db: AsyncSession) -> None:
    user = await _create_user(db)
    assert user.id is not None
    assert user.username == "testuser"
    assert user.is_active is True
    assert user.is_admin is False


async def test_create_project_with_owner(db: AsyncSession) -> None:
    user = await _create_user(db)
    project = await _create_project(db, user)
    assert project.owner_id == user.id
    assert project.is_active is True


async def test_create_agent_with_check_constraint(db: AsyncSession) -> None:
    user = await _create_user(db)
    project = await _create_project(db, user)

    agent = Agent(
        name="Test Architect",
        type="architect",
        model_config_json={"model": "test-model"},
        project_id=project.id,
    )
    db.add(agent)
    await db.flush()
    assert agent.type == "architect"


async def test_agent_invalid_type_rejected(db: AsyncSession) -> None:
    user = await _create_user(db)
    project = await _create_project(db, user)

    agent = Agent(
        name="Bad Agent",
        type="invalid_type",
        model_config_json={},
        project_id=project.id,
    )
    db.add(agent)
    with pytest.raises(Exception):
        await db.flush()


async def test_message_in_conversation(db: AsyncSession) -> None:
    user = await _create_user(db)
    project = await _create_project(db, user)

    conv = Conversation(
        title="Test Conversation",
        type="general",
        project_id=project.id,
        created_by_user_id=user.id,
    )
    db.add(conv)
    await db.flush()

    msg = Message(
        conversation_id=conv.id,
        author_type="user",
        user_id=user.id,
        content="Hello world",
        tokens_in=100,
        tokens_out=200,
        cost_usd=Decimal("0.001"),
    )
    db.add(msg)
    await db.flush()
    assert msg.conversation_id == conv.id


async def test_budget_limit_constraints(db: AsyncSession) -> None:
    budget = BudgetLimit(
        name="Test Limit",
        scope_type="global",
        amount_usd=Decimal("50.00"),
        period="daily",
        alert_threshold=Decimal("0.80"),
        action_on_exceed="warn",
    )
    db.add(budget)
    await db.flush()
    assert budget.is_active is True


async def test_task_status_constraint(db: AsyncSession) -> None:
    user = await _create_user(db)
    project = await _create_project(db, user)

    task = Task(
        title="Test Task",
        status="pending",
        priority="high",
        project_id=project.id,
    )
    db.add(task)
    await db.flush()
    assert task.status == "pending"


async def test_notification_with_user(db: AsyncSession) -> None:
    user = await _create_user(db)

    notif = Notification(
        type="budget_alert",
        title="Budget Warning",
        message="You are at 80% of daily budget",
        severity="warning",
        user_id=user.id,
    )
    db.add(notif)
    await db.flush()
    assert notif.is_read is False


async def test_conversation_participant(db: AsyncSession) -> None:
    user = await _create_user(db)
    project = await _create_project(db, user)

    agent = Agent(
        name="Architect",
        type="architect",
        model_config_json={},
        project_id=project.id,
    )
    db.add(agent)

    conv = Conversation(
        title="Chat",
        type="general",
        project_id=project.id,
    )
    db.add(conv)
    await db.flush()

    participant = ConversationParticipant(
        conversation_id=conv.id,
        agent_id=agent.id,
    )
    db.add(participant)
    await db.flush()
    assert participant.conversation_id == conv.id
    assert participant.agent_id == agent.id
