"""GitHub webhook endpoint — no JWT auth, HMAC signature verification."""

import logging

from fastapi import APIRouter, BackgroundTasks, Request

from app.core.exceptions import MCCError
from app.db.session import async_session
from app.models.github import WebhookResponse
from app.services import webhook_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github", response_model=WebhookResponse, status_code=202)
async def receive_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Receive and process a GitHub webhook.

    No JWT auth — uses HMAC-SHA256 signature verification instead.
    Always returns 202 to prevent GitHub from disabling the webhook.
    """
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    event_type = request.headers.get("X-GitHub-Event", "ping")

    if not webhook_service.verify_github_signature(body, signature):
        raise MCCError(
            code="INVALID_SIGNATURE",
            message="Invalid webhook signature",
            status_code=401,
        )

    # Ping event — just acknowledge
    if event_type == "ping":
        return WebhookResponse(status="pong")

    payload = await request.json()

    # Identify project by repository full name
    repo_full_name = payload.get("repository", {}).get("full_name")
    if not repo_full_name:
        return WebhookResponse(status="ignored")

    async with async_session() as db:
        project = await webhook_service.find_project_by_repo(db, repo_full_name)
        if not project:
            # Return 202 for unknown repos to prevent GitHub from disabling
            return WebhookResponse(status="ignored")

        webhook = await webhook_service.store_webhook(db, project.id, event_type, payload)
        webhook_id = webhook.id

    # Process in background with a fresh session
    async def _process_in_background():
        try:
            async with async_session() as db:
                await webhook_service.process_webhook(db, webhook_id)
        except Exception:
            logger.exception("Error processing webhook %s in background", webhook_id)

    background_tasks.add_task(_process_in_background)

    return WebhookResponse(status="accepted", webhook_id=webhook_id)
