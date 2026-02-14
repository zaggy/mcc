"""Tests for @mention parsing and agent resolution."""

import uuid

from app.agents.mention import parse_mentions, resolve_mentioned_agents


def test_parse_single_mention():
    assert parse_mentions("Hey @Architect, please review") == ["architect"]


def test_parse_multiple_mentions():
    result = parse_mentions("@Coder and @Tester please check this")
    assert result == ["coder", "tester"]


def test_parse_no_mentions():
    assert parse_mentions("No mentions here") == []


def test_parse_skips_email():
    result = parse_mentions("Contact user@example.com for details")
    assert result == []


def test_parse_mention_at_start():
    assert parse_mentions("@reviewer look at this") == ["reviewer"]


def test_parse_mention_with_underscore():
    assert parse_mentions("@code_reviewer check") == ["code_reviewer"]


def test_parse_mixed_email_and_mention():
    result = parse_mentions("user@test.com and @Architect should review")
    assert result == ["architect"]


def test_parse_duplicate_mentions():
    result = parse_mentions("@Architect and @Architect again")
    assert result == ["architect", "architect"]


def test_resolve_by_name():
    agent_id = uuid.uuid4()
    participants = [
        {"agent_id": agent_id, "name": "Architect", "type": "architect"},
        {"agent_id": uuid.uuid4(), "name": "Coder", "type": "coder"},
    ]
    result = resolve_mentioned_agents(["architect"], participants)
    assert result == [agent_id]


def test_resolve_by_type():
    agent_id = uuid.uuid4()
    participants = [
        {"agent_id": agent_id, "name": "MyBuilder", "type": "coder"},
    ]
    result = resolve_mentioned_agents(["coder"], participants)
    assert result == [agent_id]


def test_resolve_no_match():
    participants = [
        {"agent_id": uuid.uuid4(), "name": "Architect", "type": "architect"},
    ]
    result = resolve_mentioned_agents(["unknown"], participants)
    assert result == []


def test_resolve_deduplicates():
    agent_id = uuid.uuid4()
    participants = [
        {"agent_id": agent_id, "name": "Architect", "type": "architect"},
    ]
    # Both "architect" mentions resolve to same agent
    result = resolve_mentioned_agents(["architect", "architect"], participants)
    assert result == [agent_id]


def test_resolve_multiple_agents():
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    participants = [
        {"agent_id": id1, "name": "Architect", "type": "architect"},
        {"agent_id": id2, "name": "Tester", "type": "tester"},
    ]
    result = resolve_mentioned_agents(["architect", "tester"], participants)
    assert result == [id1, id2]


def test_resolve_case_insensitive():
    agent_id = uuid.uuid4()
    participants = [
        {"agent_id": agent_id, "name": "MyArchitect", "type": "architect"},
    ]
    result = resolve_mentioned_agents(["myarchitect"], participants)
    assert result == [agent_id]
