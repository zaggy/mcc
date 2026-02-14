"""Agent status WebSocket event emission."""

import logging
import uuid

logger = logging.getLogger(__name__)


async def emit_agent_status(
    conversation_id: uuid.UUID,
    agent_id: uuid.UUID,
    status: str,
    *,
    error_message: str | None = None,
) -> None:
    """Emit an agent_status WebSocket event to the conversation room.

    Args:
        conversation_id: Target conversation room.
        agent_id: The agent whose status changed.
        status: One of "thinking", "idle", "error".
        error_message: Optional error detail when status is "error".
    """
    try:
        from app.api.websocket import sio

        payload: dict = {
            "agent_id": str(agent_id),
            "conversation_id": str(conversation_id),
            "status": status,
        }
        if error_message:
            payload["error_message"] = error_message

        room = str(conversation_id)
        await sio.emit("agent_status", payload, room=room)
    except Exception:
        logger.debug("agent_status emit skipped (not connected)")
