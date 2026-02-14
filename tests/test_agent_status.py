"""Tests for agent status WebSocket event emission."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.services.agent_status import emit_agent_status


@pytest.fixture
def conversation_id():
    return uuid.uuid4()


@pytest.fixture
def agent_id():
    return uuid.uuid4()


async def test_emit_thinking_status(conversation_id, agent_id):
    with patch("app.api.websocket.sio") as ws_sio:
        ws_sio.emit = AsyncMock()
        await emit_agent_status(conversation_id, agent_id, "thinking")
        ws_sio.emit.assert_called_once()
        call_args = ws_sio.emit.call_args
        assert call_args[0][0] == "agent_status"
        payload = call_args[0][1]
        assert payload["status"] == "thinking"
        assert payload["agent_id"] == str(agent_id)
        assert payload["conversation_id"] == str(conversation_id)


async def test_emit_idle_status(conversation_id, agent_id):
    with patch("app.api.websocket.sio") as ws_sio:
        ws_sio.emit = AsyncMock()
        await emit_agent_status(conversation_id, agent_id, "idle")
        payload = ws_sio.emit.call_args[0][1]
        assert payload["status"] == "idle"


async def test_emit_error_status_with_message(conversation_id, agent_id):
    with patch("app.api.websocket.sio") as ws_sio:
        ws_sio.emit = AsyncMock()
        await emit_agent_status(
            conversation_id, agent_id, "error", error_message="Something went wrong"
        )
        payload = ws_sio.emit.call_args[0][1]
        assert payload["status"] == "error"
        assert payload["error_message"] == "Something went wrong"


async def test_emit_status_no_error_message_key(conversation_id, agent_id):
    with patch("app.api.websocket.sio") as ws_sio:
        ws_sio.emit = AsyncMock()
        await emit_agent_status(conversation_id, agent_id, "idle")
        payload = ws_sio.emit.call_args[0][1]
        assert "error_message" not in payload


async def test_emit_status_silently_skips_on_error(conversation_id, agent_id):
    with patch("app.api.websocket.sio", side_effect=ImportError("no sio")):
        # Should not raise
        await emit_agent_status(conversation_id, agent_id, "thinking")


async def test_emit_uses_correct_room(conversation_id, agent_id):
    with patch("app.api.websocket.sio") as ws_sio:
        ws_sio.emit = AsyncMock()
        await emit_agent_status(conversation_id, agent_id, "thinking")
        call_kwargs = ws_sio.emit.call_args[1]
        assert call_kwargs["room"] == str(conversation_id)
