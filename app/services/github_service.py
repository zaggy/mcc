"""GitHub issue and pull-request business logic."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import MCCError
from app.db.models import (
    Agent,
    Conversation,
    ConversationParticipant,
    GithubIssue,
    Project,
    PullRequest,
    Task,
)
from app.services.github_client import GitHubClient


def _parse_repo(github_repo: str) -> tuple[str, str]:
    """Split 'owner/repo' into (owner, repo)."""
    parts = github_repo.split("/")
    if len(parts) != 2:
        raise MCCError(
            code="INVALID_REPO",
            message=f"Invalid github_repo format: {github_repo!r}, expected 'owner/repo'",
            status_code=400,
        )
    return parts[0], parts[1]


async def _get_project_or_404(db: AsyncSession, project_id: uuid.UUID) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise MCCError(code="PROJECT_NOT_FOUND", message="Project not found", status_code=404)
    return project


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ------------------------------------------------------------------
# Issues
# ------------------------------------------------------------------
async def sync_issues(
    db: AsyncSession,
    github: GitHubClient,
    project_id: uuid.UUID,
    *,
    state: str = "open",
    label: str | None = None,
) -> list[GithubIssue]:
    """Fetch issues from GitHub API and upsert into local DB."""
    project = await _get_project_or_404(db, project_id)
    owner, repo = _parse_repo(project.github_repo)

    raw_issues = await github.list_issues(owner, repo, state=state, labels=label)

    upserted: list[GithubIssue] = []
    for item in raw_issues:
        # GitHub returns PRs in the issues endpoint — skip them
        if "pull_request" in item:
            continue

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
            upserted.append(existing)
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
            upserted.append(issue)

    await db.commit()
    for obj in upserted:
        await db.refresh(obj)
    return upserted


async def list_issues(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    state: str | None = None,
    label: str | None = None,
) -> list[GithubIssue]:
    """Query locally-stored issues."""
    await _get_project_or_404(db, project_id)
    query = select(GithubIssue).where(GithubIssue.project_id == project_id)
    if state:
        query = query.where(GithubIssue.state == state)
    if label:
        query = query.where(GithubIssue.labels.contains([label]))
    query = query.order_by(GithubIssue.number.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_issue(
    db: AsyncSession,
    project_id: uuid.UUID,
    issue_id: uuid.UUID,
) -> GithubIssue:
    await _get_project_or_404(db, project_id)
    issue = await db.get(GithubIssue, issue_id)
    if not issue or issue.project_id != project_id:
        raise MCCError(code="ISSUE_NOT_FOUND", message="Issue not found", status_code=404)
    return issue


async def start_issue(
    db: AsyncSession,
    project_id: uuid.UUID,
    issue_id: uuid.UUID,
) -> Conversation:
    """Create an 'issue' conversation for a GitHub issue and assign the architect."""
    issue = await get_issue(db, project_id, issue_id)

    if issue.conversation_id:
        raise MCCError(
            code="ISSUE_ALREADY_STARTED",
            message="This issue already has a conversation",
            status_code=409,
        )

    # Find architect agent for this project
    result = await db.execute(
        select(Agent).where(
            Agent.project_id == project_id,
            Agent.type == "architect",
            Agent.is_active.is_(True),
        )
    )
    architect = result.scalar_one_or_none()
    if not architect:
        raise MCCError(
            code="NO_ARCHITECT",
            message="No active architect agent found for this project",
            status_code=400,
        )

    # Create conversation
    conv = Conversation(
        title=f"Issue #{issue.number}: {issue.title}",
        type="issue",
        project_id=project_id,
    )
    db.add(conv)
    await db.flush()

    # Add architect as participant
    participant = ConversationParticipant(
        conversation_id=conv.id,
        agent_id=architect.id,
    )
    db.add(participant)

    # Link issue to conversation
    issue.conversation_id = conv.id

    await db.commit()
    await db.refresh(conv)
    return conv


# ------------------------------------------------------------------
# Pull Requests
# ------------------------------------------------------------------
async def sync_pull_requests(
    db: AsyncSession,
    github: GitHubClient,
    project_id: uuid.UUID,
    *,
    state: str = "open",
) -> list[PullRequest]:
    """Fetch PRs from GitHub API and upsert into local DB."""
    project = await _get_project_or_404(db, project_id)
    owner, repo = _parse_repo(project.github_repo)

    raw_prs = await github.list_pull_requests(owner, repo, state=state)

    upserted: list[PullRequest] = []
    for item in raw_prs:
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
            upserted.append(existing)
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
            upserted.append(pr)

    await db.commit()
    for obj in upserted:
        await db.refresh(obj)
    return upserted


async def list_pull_requests(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> list[PullRequest]:
    await _get_project_or_404(db, project_id)
    result = await db.execute(
        select(PullRequest)
        .where(PullRequest.project_id == project_id)
        .order_by(PullRequest.number.desc())
    )
    return list(result.scalars().all())


async def approve_pull_request(
    db: AsyncSession,
    github: GitHubClient,
    project_id: uuid.UUID,
    pr_id: uuid.UUID,
) -> PullRequest:
    """Submit APPROVE review and attempt merge."""
    project = await _get_project_or_404(db, project_id)
    pr = await db.get(PullRequest, pr_id)
    if not pr or pr.project_id != project_id:
        raise MCCError(code="PR_NOT_FOUND", message="Pull request not found", status_code=404)

    owner, repo = _parse_repo(project.github_repo)

    await github.create_review(owner, repo, pr.number, event="APPROVE")
    await github.merge_pull_request(owner, repo, pr.number)

    pr.state = "closed"
    pr.review_status = "approved"
    pr.merged_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(pr)
    return pr


async def reject_pull_request(
    db: AsyncSession,
    github: GitHubClient,
    project_id: uuid.UUID,
    pr_id: uuid.UUID,
    feedback: str,
) -> PullRequest:
    """Submit REQUEST_CHANGES review."""
    project = await _get_project_or_404(db, project_id)
    pr = await db.get(PullRequest, pr_id)
    if not pr or pr.project_id != project_id:
        raise MCCError(code="PR_NOT_FOUND", message="Pull request not found", status_code=404)

    owner, repo = _parse_repo(project.github_repo)

    await github.create_review(owner, repo, pr.number, event="REQUEST_CHANGES", body=feedback)

    pr.review_status = "changes_requested"
    await db.commit()
    await db.refresh(pr)
    return pr


# ------------------------------------------------------------------
# Tasks
# ------------------------------------------------------------------
async def list_issue_tasks(
    db: AsyncSession,
    project_id: uuid.UUID,
    issue_id: uuid.UUID,
) -> list[Task]:
    await _get_project_or_404(db, project_id)
    issue = await db.get(GithubIssue, issue_id)
    if not issue or issue.project_id != project_id:
        raise MCCError(code="ISSUE_NOT_FOUND", message="Issue not found", status_code=404)

    result = await db.execute(
        select(Task).where(Task.issue_id == issue_id).order_by(Task.created_at)
    )
    return list(result.scalars().all())
