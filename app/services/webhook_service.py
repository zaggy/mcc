"""GitHub webhook verification, storage, and event processing."""

import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import GithubIssue, Project, PullRequest, Webhook

logger = logging.getLogger(__name__)


def verify_github_signature(payload_body: bytes, signature_header: str | None) -> bool:
    """Verify HMAC-SHA256 signature from GitHub webhook.

    If no webhook secret is configured, allow through (dev mode).
    """
    if not settings.GITHUB_WEBHOOK_SECRET:
        return True

    if not signature_header:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature_header)


async def find_project_by_repo(db: AsyncSession, repo_full_name: str) -> Project | None:
    """Look up a project by its github_repo field."""
    result = await db.execute(select(Project).where(Project.github_repo == repo_full_name))
    return result.scalar_one_or_none()


async def store_webhook(
    db: AsyncSession,
    project_id: uuid.UUID,
    event_type: str,
    payload: dict,
) -> Webhook:
    """Persist a raw webhook event."""
    webhook = Webhook(
        project_id=project_id,
        source="github",
        event_type=event_type,
        payload=payload,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return webhook


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def process_webhook(db: AsyncSession, webhook_id: uuid.UUID) -> None:
    """Dispatch a stored webhook to the appropriate event handler."""
    webhook = await db.get(Webhook, webhook_id)
    if not webhook:
        logger.warning("Webhook %s not found", webhook_id)
        return

    if webhook.processed:
        return

    try:
        event_type = webhook.event_type
        payload = webhook.payload

        if event_type == "issues":
            await _handle_issue_event(db, webhook.project_id, payload)
        elif event_type == "issue_comment":
            await _handle_issue_comment_event(db, webhook.project_id, payload)
        elif event_type == "pull_request":
            await _handle_pull_request_event(db, webhook.project_id, payload)
        elif event_type == "pull_request_review":
            await _handle_pr_review_event(db, webhook.project_id, payload)
        else:
            logger.info("Ignoring unhandled webhook event type: %s", event_type)

        webhook.processed = True
        webhook.processed_at = datetime.now(UTC)
        await db.commit()

    except Exception:
        webhook.retry_count += 1
        if webhook.retry_count >= webhook.max_retries:
            webhook.processed = True
            webhook.error_message = "Max retries exceeded"
            webhook.processed_at = datetime.now(UTC)
        await db.commit()
        logger.exception("Error processing webhook %s", webhook_id)


# ------------------------------------------------------------------
# Event handlers
# ------------------------------------------------------------------
async def _handle_issue_event(db: AsyncSession, project_id: uuid.UUID, payload: dict) -> None:
    """Upsert GithubIssue on opened/edited/closed/reopened."""
    action = payload.get("action")
    if action not in ("opened", "edited", "closed", "reopened"):
        return

    item = payload["issue"]
    result = await db.execute(
        select(GithubIssue).where(
            GithubIssue.project_id == project_id,
            GithubIssue.number == item["number"],
        )
    )
    existing = result.scalar_one_or_none()

    labels = [lbl["name"] for lbl in item.get("labels", [])]
    assignee = item["assignee"]["login"] if item.get("assignee") else None

    if existing:
        existing.title = item["title"]
        existing.body = item.get("body")
        existing.state = item["state"]
        existing.labels = labels
        existing.assignee = assignee
        existing.github_updated_at = _parse_dt(item.get("updated_at"))
    else:
        issue = GithubIssue(
            github_id=item["id"],
            number=item["number"],
            title=item["title"],
            body=item.get("body"),
            state=item["state"],
            labels=labels,
            assignee=assignee,
            project_id=project_id,
            github_created_at=_parse_dt(item.get("created_at")),
            github_updated_at=_parse_dt(item.get("updated_at")),
        )
        db.add(issue)

    await db.flush()


async def _handle_issue_comment_event(
    db: AsyncSession, project_id: uuid.UUID, payload: dict
) -> None:
    """Log issue comment — future: inject into conversation."""
    comment = payload.get("comment", {})
    issue = payload.get("issue", {})
    logger.info(
        "Issue comment on #%s by %s (project %s)",
        issue.get("number"),
        comment.get("user", {}).get("login"),
        project_id,
    )


async def _handle_pull_request_event(
    db: AsyncSession, project_id: uuid.UUID, payload: dict
) -> None:
    """Upsert PullRequest on opened/closed/synchronize."""
    action = payload.get("action")
    if action not in ("opened", "closed", "synchronize", "reopened"):
        return

    item = payload["pull_request"]
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.project_id == project_id,
            PullRequest.number == item["number"],
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.title = item["title"]
        existing.body = item.get("body")
        existing.state = item["state"]
        existing.is_draft = item.get("draft", False)
        merged_at = _parse_dt(item.get("merged_at"))
        if merged_at:
            existing.merged_at = merged_at
    else:
        pr = PullRequest(
            github_id=item["id"],
            number=item["number"],
            title=item["title"],
            body=item.get("body"),
            branch_from=item["head"]["ref"],
            branch_to=item["base"]["ref"],
            state=item["state"],
            is_draft=item.get("draft", False),
            project_id=project_id,
            merged_at=_parse_dt(item.get("merged_at")),
            github_created_at=_parse_dt(item.get("created_at")),
        )
        db.add(pr)

    await db.flush()


async def _handle_pr_review_event(db: AsyncSession, project_id: uuid.UUID, payload: dict) -> None:
    """Update PullRequest.review_status based on review state."""
    review = payload.get("review", {})
    pr_data = payload.get("pull_request", {})

    result = await db.execute(
        select(PullRequest).where(
            PullRequest.project_id == project_id,
            PullRequest.number == pr_data.get("number"),
        )
    )
    pr = result.scalar_one_or_none()
    if not pr:
        return

    state = review.get("state", "").lower()
    if state == "approved":
        pr.review_status = "approved"
    elif state == "changes_requested":
        pr.review_status = "changes_requested"
    elif state == "commented":
        pass  # Don't change status on comments
    elif state == "dismissed":
        pr.review_status = None

    await db.flush()
