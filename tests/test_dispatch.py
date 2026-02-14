"""Integration tests for dispatch target resolution."""

import psycopg2
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import Agent, Conversation, ConversationParticipant, Project, User
from app.db.session import Base
from app.services.dispatch_service import resolve_dispatch_targets

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


async def _setup_conversation(db: AsyncSession):
    """Create a user, project, agents, and a conversation with participants."""
    user = User(username="dispatchuser", email="dispatch@test.com", password_hash="fakehash")
    db.add(user)
    await db.flush()

    project = Project(name="Dispatch Project", github_repo="test/dispatch", owner_id=user.id)
    db.add(project)
    await db.flush()

    architect = Agent(
        name="Architect", type="architect", model_config_json={}, project_id=project.id
    )
    coder = Agent(name="Coder", type="coder", model_config_json={}, project_id=project.id)
    tester = Agent(name="Tester", type="tester", model_config_json={}, project_id=project.id)
    db.add_all([architect, coder, tester])
    await db.flush()

    conv = Conversation(
        title="Test Conv", type="general", project_id=project.id, created_by_user_id=user.id
    )
    db.add(conv)
    await db.flush()

    for agent in [architect, coder, tester]:
        db.add(ConversationParticipant(conversation_id=conv.id, agent_id=agent.id))
    await db.flush()

    return conv, architect, coder, tester


async def test_no_mentions_dispatches_to_all(db: AsyncSession):
    conv, architect, coder, tester = await _setup_conversation(db)

    result = await resolve_dispatch_targets(db, conv.id, "Hello everyone!")
    assert set(result) == {architect.id, coder.id, tester.id}


async def test_single_mention_dispatches_to_one(db: AsyncSession):
    conv, architect, coder, tester = await _setup_conversation(db)

    result = await resolve_dispatch_targets(db, conv.id, "Hey @Architect, review this")
    assert result == [architect.id]


async def test_multiple_mentions_dispatch(db: AsyncSession):
    conv, architect, coder, tester = await _setup_conversation(db)

    result = await resolve_dispatch_targets(db, conv.id, "@Coder and @Tester work together")
    assert set(result) == {coder.id, tester.id}


async def test_mention_by_type(db: AsyncSession):
    conv, architect, coder, tester = await _setup_conversation(db)

    result = await resolve_dispatch_targets(db, conv.id, "@tester please check")
    assert result == [tester.id]


async def test_unresolved_mention_falls_back_to_all(db: AsyncSession):
    conv, architect, coder, tester = await _setup_conversation(db)

    result = await resolve_dispatch_targets(db, conv.id, "@unknown_agent do something")
    assert set(result) == {architect.id, coder.id, tester.id}


async def test_empty_conversation_returns_empty(db: AsyncSession):
    user = User(username="emptyuser", email="empty@test.com", password_hash="fakehash")
    db.add(user)
    await db.flush()

    project = Project(name="Empty Project", github_repo="test/empty", owner_id=user.id)
    db.add(project)
    await db.flush()

    conv = Conversation(
        title="Empty Conv", type="general", project_id=project.id, created_by_user_id=user.id
    )
    db.add(conv)
    await db.flush()

    result = await resolve_dispatch_targets(db, conv.id, "@Architect hello")
    assert result == []
