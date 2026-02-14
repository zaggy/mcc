"""Integration tests for budget service."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import psycopg2
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import Agent, BudgetLimit, Project, TokenUsage, User
from app.db.session import Base
from app.services.budget_service import _period_start, check_budget

_base = settings.DATABASE_URL.rsplit("/", 1)[0]
TEST_DB_URL = f"{_base}/mcc_test"

# Ensure test DB exists
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


async def _create_agent(db: AsyncSession, agent_type: str = "coder") -> Agent:
    """Create user, project, and agent for budget tests."""
    user = User(
        username=f"budgetuser_{uuid.uuid4().hex[:8]}",
        email=f"budget_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="fakehash",
    )
    db.add(user)
    await db.flush()

    project = Project(name="Budget Project", github_repo="test/budget", owner_id=user.id)
    db.add(project)
    await db.flush()

    agent = Agent(
        name="Test Agent",
        type=agent_type,
        model_config_json={},
        project_id=project.id,
    )
    db.add(agent)
    await db.flush()
    return agent


def test_period_start_daily():
    start = _period_start("daily")
    now = datetime.now(UTC)
    assert start.hour == 0
    assert start.minute == 0
    assert start.day == now.day


def test_period_start_weekly():
    start = _period_start("weekly")
    # weekday() returns 0 for Monday
    assert start.weekday() == 0
    assert start.hour == 0


def test_period_start_monthly():
    start = _period_start("monthly")
    assert start.day == 1
    assert start.hour == 0


async def test_no_limits_allows(db: AsyncSession):
    result = await check_budget(
        db, agent_id=uuid.uuid4(), agent_type="coder", project_id=uuid.uuid4()
    )
    assert result.allowed is True
    assert result.warnings == []


async def test_under_budget_allows(db: AsyncSession):
    agent = await _create_agent(db)

    limit = BudgetLimit(
        name="Agent Limit",
        scope_type="agent",
        scope_id=agent.id,
        amount_usd=Decimal("10.00"),
        period="daily",
        alert_threshold=Decimal("0.80"),
        action_on_exceed="block",
    )
    db.add(limit)
    await db.flush()

    # Add minimal usage
    usage = TokenUsage(
        timestamp=datetime.now(UTC),
        usage_date=datetime.now(UTC).date(),
        agent_id=agent.id,
        agent_type="coder",
        model="test-model",
        tokens_in=100,
        tokens_out=50,
        cost_usd=Decimal("1.00"),
    )
    db.add(usage)
    await db.flush()

    result = await check_budget(db, agent_id=agent.id, agent_type="coder")
    assert result.allowed is True


async def test_over_budget_blocks(db: AsyncSession):
    agent = await _create_agent(db)

    limit = BudgetLimit(
        name="Agent Limit",
        scope_type="agent",
        scope_id=agent.id,
        amount_usd=Decimal("5.00"),
        period="daily",
        alert_threshold=Decimal("0.80"),
        action_on_exceed="block",
    )
    db.add(limit)
    await db.flush()

    usage = TokenUsage(
        timestamp=datetime.now(UTC),
        usage_date=datetime.now(UTC).date(),
        agent_id=agent.id,
        agent_type="coder",
        model="test-model",
        tokens_in=10000,
        tokens_out=5000,
        cost_usd=Decimal("6.00"),
    )
    db.add(usage)
    await db.flush()

    result = await check_budget(db, agent_id=agent.id, agent_type="coder")
    assert result.allowed is False
    assert len(result.warnings) > 0
    assert "exceeded" in result.warnings[0]


async def test_over_budget_warn_allows(db: AsyncSession):
    agent = await _create_agent(db)

    limit = BudgetLimit(
        name="Warn Limit",
        scope_type="agent",
        scope_id=agent.id,
        amount_usd=Decimal("5.00"),
        period="daily",
        alert_threshold=Decimal("0.80"),
        action_on_exceed="warn",
    )
    db.add(limit)
    await db.flush()

    usage = TokenUsage(
        timestamp=datetime.now(UTC),
        usage_date=datetime.now(UTC).date(),
        agent_id=agent.id,
        agent_type="coder",
        model="test-model",
        tokens_in=10000,
        tokens_out=5000,
        cost_usd=Decimal("6.00"),
    )
    db.add(usage)
    await db.flush()

    result = await check_budget(db, agent_id=agent.id, agent_type="coder")
    # warn mode doesn't block
    assert result.allowed is True


async def test_alert_threshold_warning(db: AsyncSession):
    agent = await _create_agent(db)

    limit = BudgetLimit(
        name="Threshold Limit",
        scope_type="agent",
        scope_id=agent.id,
        amount_usd=Decimal("10.00"),
        period="daily",
        alert_threshold=Decimal("0.80"),
        action_on_exceed="block",
    )
    db.add(limit)
    await db.flush()

    # 85% usage — over threshold, under limit
    usage = TokenUsage(
        timestamp=datetime.now(UTC),
        usage_date=datetime.now(UTC).date(),
        agent_id=agent.id,
        agent_type="coder",
        model="test-model",
        tokens_in=5000,
        tokens_out=2500,
        cost_usd=Decimal("8.50"),
    )
    db.add(usage)
    await db.flush()

    result = await check_budget(db, agent_id=agent.id, agent_type="coder")
    assert result.allowed is True
    assert len(result.warnings) > 0
    assert "85%" in result.warnings[0]
