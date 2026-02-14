"""Integration tests for agent memory service."""

from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import Agent, Project, User
from app.db.session import Base
from app.models.memory import MemoryCreate, MemoryUpdate
from app.services.memory_service import (
    build_memory_context,
    delete_agent_memories,
    delete_memory,
    get_memories,
    get_memory,
    store_memory,
    update_memory,
)

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


async def _create_agent(db: AsyncSession):
    user = User(username="memuser", email="mem@test.com", password_hash="fakehash")
    db.add(user)
    await db.flush()

    project = Project(name="Mem Project", github_repo="test/mem", owner_id=user.id)
    db.add(project)
    await db.flush()

    agent = Agent(name="Architect", type="architect", model_config_json={}, project_id=project.id)
    db.add(agent)
    await db.flush()

    return agent, project


async def test_store_memory(db: AsyncSession):
    agent, project = await _create_agent(db)
    data = MemoryCreate(category="code", key="main_language", value={"lang": "python"})
    memory = await store_memory(db, agent.id, project.id, data)
    assert memory.category == "code"
    assert memory.key == "main_language"
    assert memory.value == {"lang": "python"}
    assert memory.importance == 5


async def test_store_memory_upsert(db: AsyncSession):
    agent, project = await _create_agent(db)
    data1 = MemoryCreate(category="code", key="framework", value={"name": "fastapi"})
    mem1 = await store_memory(db, agent.id, project.id, data1)

    data2 = MemoryCreate(category="code", key="framework", value={"name": "django"}, importance=8)
    mem2 = await store_memory(db, agent.id, project.id, data2)

    assert mem1.id == mem2.id
    assert mem2.value == {"name": "django"}
    assert mem2.importance == 8


async def test_get_memories(db: AsyncSession):
    agent, project = await _create_agent(db)
    for i in range(3):
        data = MemoryCreate(category="test", key=f"key_{i}", value={"i": i}, importance=i + 1)
        await store_memory(db, agent.id, project.id, data)

    memories = await get_memories(db, agent.id, project_id=project.id)
    assert len(memories) == 3
    # Ordered by importance DESC
    assert memories[0].importance >= memories[1].importance


async def test_get_memories_filter_category(db: AsyncSession):
    agent, project = await _create_agent(db)
    await store_memory(
        db, agent.id, project.id, MemoryCreate(category="code", key="k1", value={"a": 1})
    )
    await store_memory(
        db, agent.id, project.id, MemoryCreate(category="style", key="k2", value={"b": 2})
    )

    code_mems = await get_memories(db, agent.id, project_id=project.id, category="code")
    assert len(code_mems) == 1
    assert code_mems[0].category == "code"


async def test_get_memories_filter_importance(db: AsyncSession):
    agent, project = await _create_agent(db)
    await store_memory(
        db,
        agent.id,
        project.id,
        MemoryCreate(category="test", key="low", value={}, importance=2),
    )
    await store_memory(
        db,
        agent.id,
        project.id,
        MemoryCreate(category="test", key="high", value={}, importance=8),
    )

    high_mems = await get_memories(db, agent.id, project_id=project.id, min_importance=5)
    assert len(high_mems) == 1
    assert high_mems[0].key == "high"


async def test_get_memories_excludes_expired(db: AsyncSession):
    agent, project = await _create_agent(db)
    past = datetime.now(UTC) - timedelta(hours=1)
    await store_memory(
        db,
        agent.id,
        project.id,
        MemoryCreate(category="test", key="expired", value={}, expires_at=past),
    )
    await store_memory(
        db,
        agent.id,
        project.id,
        MemoryCreate(category="test", key="valid", value={}),
    )

    memories = await get_memories(db, agent.id, project_id=project.id)
    assert len(memories) == 1
    assert memories[0].key == "valid"


async def test_update_memory(db: AsyncSession):
    agent, project = await _create_agent(db)
    data = MemoryCreate(category="test", key="k1", value={"old": True})
    mem = await store_memory(db, agent.id, project.id, data)

    updated = await update_memory(db, mem.id, MemoryUpdate(value={"new": True}, importance=9))
    assert updated is not None
    assert updated.value == {"new": True}
    assert updated.importance == 9


async def test_update_nonexistent_returns_none(db: AsyncSession):
    import uuid

    result = await update_memory(db, uuid.uuid4(), MemoryUpdate(value={"x": 1}))
    assert result is None


async def test_delete_memory(db: AsyncSession):
    agent, project = await _create_agent(db)
    data = MemoryCreate(category="test", key="to_delete", value={})
    mem = await store_memory(db, agent.id, project.id, data)

    assert await delete_memory(db, mem.id) is True
    assert await get_memory(db, mem.id) is None


async def test_delete_nonexistent_returns_false(db: AsyncSession):
    import uuid

    assert await delete_memory(db, uuid.uuid4()) is False


async def test_delete_agent_memories(db: AsyncSession):
    agent, project = await _create_agent(db)
    for i in range(5):
        data = MemoryCreate(category="test", key=f"k{i}", value={})
        await store_memory(db, agent.id, project.id, data)

    count = await delete_agent_memories(db, agent.id)
    assert count == 5

    remaining = await get_memories(db, agent.id)
    assert len(remaining) == 0


async def test_build_memory_context_empty(db: AsyncSession):
    agent, project = await _create_agent(db)
    result = await build_memory_context(db, agent.id, project.id)
    assert result == ""


async def test_build_memory_context_with_memories(db: AsyncSession):
    agent, project = await _create_agent(db)
    await store_memory(
        db,
        agent.id,
        project.id,
        MemoryCreate(category="code", key="lang", value={"name": "python"}, importance=8),
    )
    await store_memory(
        db,
        agent.id,
        project.id,
        MemoryCreate(category="style", key="format", value={"tool": "ruff"}, importance=6),
    )

    result = await build_memory_context(db, agent.id, project.id)
    assert "## Agent Memory" in result
    assert "lang" in result
    assert "format" in result
