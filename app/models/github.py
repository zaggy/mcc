"""Pydantic schemas for GitHub issues, pull requests, tasks, and webhooks."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# GitHub Issues
# ---------------------------------------------------------------------------
class GithubIssueRead(BaseModel):
    id: uuid.UUID
    github_id: int
    number: int
    title: str
    body: str | None
    state: str
    labels: list | dict
    assignee: str | None
    project_id: uuid.UUID
    conversation_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    github_created_at: datetime | None
    github_updated_at: datetime | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Pull Requests
# ---------------------------------------------------------------------------
class PullRequestRead(BaseModel):
    id: uuid.UUID
    github_id: int
    number: int
    title: str
    body: str | None
    branch_from: str
    branch_to: str
    state: str
    is_draft: bool
    review_status: str | None
    test_status: str | None
    project_id: uuid.UUID
    issue_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    merged_at: datetime | None
    github_created_at: datetime | None

    model_config = {"from_attributes": True}


class PRRejectRequest(BaseModel):
    feedback: str


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
class TaskRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: str
    priority: str
    assigned_to_agent_id: uuid.UUID | None
    issue_id: uuid.UUID | None
    pr_id: uuid.UUID | None
    definition_of_done: str | None
    total_tokens_used: int
    total_cost_usd: Decimal
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------
class WebhookResponse(BaseModel):
    status: str
    webhook_id: uuid.UUID | None = None
