"""GitHub issue endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_github
from app.db.models import User
from app.db.session import get_db
from app.models.conversation import ConversationRead
from app.models.github import GithubIssueRead, TaskRead
from app.services import github_service
from app.services.github_client import GitHubClient

router = APIRouter(
    prefix="/projects/{project_id}/issues",
    tags=["issues"],
)


@router.get("", response_model=list[GithubIssueRead])
async def list_issues(
    project_id: uuid.UUID,
    sync: bool = Query(True, description="Sync from GitHub before returning"),
    state: str = Query("open"),
    label: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    github: GitHubClient = Depends(get_github),
):
    if sync:
        return await github_service.sync_issues(db, github, project_id, state=state, label=label)
    return await github_service.list_issues(db, project_id, state=state, label=label)


@router.post("/{issue_id}/start", response_model=ConversationRead, status_code=201)
async def start_issue(
    project_id: uuid.UUID,
    issue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await github_service.start_issue(db, project_id, issue_id)


@router.get("/{issue_id}/tasks", response_model=list[TaskRead])
async def list_issue_tasks(
    project_id: uuid.UUID,
    issue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await github_service.list_issue_tasks(db, project_id, issue_id)
