"""Pull request endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_github
from app.db.models import User
from app.db.session import get_db
from app.models.github import PRRejectRequest, PullRequestRead
from app.services import github_service
from app.services.github_client import GitHubClient

router = APIRouter(
    prefix="/projects/{project_id}/pull-requests",
    tags=["pull-requests"],
)


@router.get("", response_model=list[PullRequestRead])
async def list_pull_requests(
    project_id: uuid.UUID,
    sync: bool = Query(True, description="Sync from GitHub before returning"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    github: GitHubClient = Depends(get_github),
):
    if sync:
        return await github_service.sync_pull_requests(db, github, project_id)
    return await github_service.list_pull_requests(db, project_id)


@router.post("/{pr_id}/approve", response_model=PullRequestRead)
async def approve_pull_request(
    project_id: uuid.UUID,
    pr_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    github: GitHubClient = Depends(get_github),
):
    return await github_service.approve_pull_request(db, github, project_id, pr_id)


@router.post("/{pr_id}/reject", response_model=PullRequestRead)
async def reject_pull_request(
    project_id: uuid.UUID,
    pr_id: uuid.UUID,
    data: PRRejectRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    github: GitHubClient = Depends(get_github),
):
    return await github_service.reject_pull_request(db, github, project_id, pr_id, data.feedback)
