"""Tests for agent registry and factory."""

from unittest.mock import MagicMock

from app.agents.architect import ArchitectAgent
from app.agents.coder import CoderAgent
from app.agents.registry import AGENT_REGISTRY, create_agent
from app.agents.reviewer import ReviewerAgent
from app.agents.tester import TesterAgent


def _make_agent_record(agent_type: str, name: str = "Test Agent"):
    """Create a mock Agent DB record."""
    mock = MagicMock()
    mock.id = "00000000-0000-0000-0000-000000000001"
    mock.type = agent_type
    mock.name = name
    mock.project_id = None
    mock.system_prompt = None
    mock.model_config_json = {}
    return mock


def test_registry_contains_all_types():
    expected = {"orchestrator", "architect", "coder", "tester", "reviewer"}
    assert set(AGENT_REGISTRY.keys()) == expected


def test_create_architect():
    record = _make_agent_record("architect")
    openrouter = MagicMock()
    agent = create_agent(record, openrouter)
    assert isinstance(agent, ArchitectAgent)


def test_create_coder():
    record = _make_agent_record("coder")
    openrouter = MagicMock()
    agent = create_agent(record, openrouter)
    assert isinstance(agent, CoderAgent)


def test_create_tester():
    record = _make_agent_record("tester")
    openrouter = MagicMock()
    agent = create_agent(record, openrouter)
    assert isinstance(agent, TesterAgent)


def test_create_reviewer():
    record = _make_agent_record("reviewer")
    openrouter = MagicMock()
    agent = create_agent(record, openrouter)
    assert isinstance(agent, ReviewerAgent)


def test_create_unknown_type_raises():
    record = _make_agent_record("nonexistent")
    openrouter = MagicMock()
    try:
        create_agent(record, openrouter)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown agent type" in str(e)


def test_architect_system_prompt():
    record = _make_agent_record("architect")
    openrouter = MagicMock()
    agent = create_agent(record, openrouter)
    prompt = agent.default_system_prompt()
    assert "Architect" in prompt
    assert len(prompt) > 50


def test_architect_allowed_recipients():
    record = _make_agent_record("architect")
    openrouter = MagicMock()
    agent = create_agent(record, openrouter)
    recipients = agent.allowed_recipients()
    assert isinstance(recipients, list)
    assert len(recipients) > 0


def test_custom_system_prompt_overrides_default():
    record = _make_agent_record("architect")
    record.system_prompt = "Custom prompt override"
    openrouter = MagicMock()
    agent = create_agent(record, openrouter)
    assert agent._get_system_prompt() == "Custom prompt override"


def test_default_system_prompt_when_none():
    record = _make_agent_record("architect")
    record.system_prompt = None
    openrouter = MagicMock()
    agent = create_agent(record, openrouter)
    assert agent._get_system_prompt() == agent.default_system_prompt()
