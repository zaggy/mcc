"""Socket.io server for real-time communication with JWT authentication."""

import logging

import socketio
from jwt import InvalidTokenError

from app.core.security import decode_token

logger = logging.getLogger(__name__)

# Module-level singleton — imported by agent background tasks to emit events
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[],  # Controlled by FastAPI CORS middleware
    logger=False,
)

# ASGI app to mount on the main FastAPI application
sio_app = socketio.ASGIApp(sio, socketio_path="/")


@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None):
    """Authenticate WebSocket connections via JWT token."""
    token = None
    if auth and isinstance(auth, dict):
        token = auth.get("token")

    if not token:
        # Try query string
        query = environ.get("QUERY_STRING", "")
        for param in query.split("&"):
            if param.startswith("token="):
                token = param[6:]
                break

    if not token:
        logger.warning("WebSocket connection rejected: no token (sid=%s)", sid)
        raise socketio.exceptions.ConnectionRefusedError("Authentication required")

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise socketio.exceptions.ConnectionRefusedError("Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise socketio.exceptions.ConnectionRefusedError("Invalid token")
    except InvalidTokenError:
        logger.warning("WebSocket connection rejected: invalid token (sid=%s)", sid)
        raise socketio.exceptions.ConnectionRefusedError("Invalid or expired token")

    # Store user_id in session
    await sio.save_session(sid, {"user_id": user_id})
    logger.info("WebSocket connected: sid=%s user=%s", sid, user_id)


@sio.event
async def disconnect(sid: str):
    logger.info("WebSocket disconnected: sid=%s", sid)


@sio.event
async def join_conversation(sid: str, data: dict):
    """Join a conversation room to receive real-time updates."""
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return
    room = str(conversation_id)
    sio.enter_room(sid, room)
    logger.info("sid=%s joined room %s", sid, room)
    await sio.emit("joined", {"conversation_id": conversation_id}, room=sid)


@sio.event
async def leave_conversation(sid: str, data: dict):
    """Leave a conversation room."""
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return
    room = str(conversation_id)
    sio.leave_room(sid, room)
    logger.info("sid=%s left room %s", sid, room)


@sio.event
async def typing(sid: str, data: dict):
    """Broadcast typing indicator to conversation room."""
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return
    room = str(conversation_id)
    session = await sio.get_session(sid)
    await sio.emit(
        "typing",
        {"user_id": session.get("user_id"), "conversation_id": conversation_id},
        room=room,
        skip_sid=sid,
    )
