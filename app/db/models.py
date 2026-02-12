"""SQLAlchemy 2.0 models for all 13+ tables."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("idx_projects_owner", "owner_id"),
        Index("idx_projects_github", "github_repo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_repo: Mapped[str] = mapped_column(String(255), nullable=False)
    github_app_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    github_installation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    local_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="projects")
    agents: Mapped[list["Agent"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    github_issues: Mapped[list["GithubIssue"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    pull_requests: Mapped[list["PullRequest"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    webhooks: Mapped[list["Webhook"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------
class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        CheckConstraint(
            "type IN ('orchestrator', 'architect', 'coder', 'tester', 'reviewer')",
            name="ck_agents_type",
        ),
        Index("idx_agents_project", "project_id"),
        Index("idx_agents_type", "type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    model_config_json: Mapped[dict] = mapped_column(
        "model_config", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project | None"] = relationship(back_populates="agents")
    messages: Mapped[list["Message"]] = relationship(back_populates="agent")
    tasks_assigned: Mapped[list["Task"]] = relationship(back_populates="assigned_to_agent")
    memories: Mapped[list["AgentMemory"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    conversation_participations: Mapped[list["ConversationParticipant"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------
class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "type IN ('issue', 'general', 'task', 'review')",
            name="ck_conversations_type",
        ),
        CheckConstraint(
            "status IN ('active', 'paused', 'completed', 'archived')",
            name="ck_conversations_status",
        ),
        Index("idx_conversations_project", "project_id"),
        Index("idx_conversations_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project | None"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    participants: Mapped[list["ConversationParticipant"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    github_issue: Mapped["GithubIssue | None"] = relationship(back_populates="conversation")


# ---------------------------------------------------------------------------
# Conversation Participants
# ---------------------------------------------------------------------------
class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="participants")
    agent: Mapped["Agent"] = relationship(back_populates="conversation_participations")


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "author_type IN ('user', 'agent')",
            name="ck_messages_author_type",
        ),
        Index("idx_messages_conversation_created", "conversation_id", "created_at"),
        Index("idx_messages_agent", "agent_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    author_type: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_formatted: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True
    )
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0, server_default="0")
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    agent: Mapped["Agent | None"] = relationship(back_populates="messages")
    reply_to: Mapped["Message | None"] = relationship(remote_side=[id])


# ---------------------------------------------------------------------------
# GitHub Issues
# ---------------------------------------------------------------------------
class GithubIssue(Base):
    __tablename__ = "github_issues"
    __table_args__ = (
        UniqueConstraint("project_id", "number", name="uq_github_issues_project_number"),
        Index("idx_issues_project", "project_id"),
        Index("idx_issues_state", "state"),
        Index("idx_issues_conversation", "conversation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", server_default="open"
    )
    labels: Mapped[dict] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    assignee: Mapped[str | None] = mapped_column(String(100), nullable=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    github_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    github_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="github_issues")
    conversation: Mapped["Conversation | None"] = relationship(back_populates="github_issue")
    pull_requests: Mapped[list["PullRequest"]] = relationship(back_populates="issue")
    tasks: Mapped[list["Task"]] = relationship(back_populates="issue")


# ---------------------------------------------------------------------------
# Pull Requests
# ---------------------------------------------------------------------------
class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("project_id", "number", name="uq_pull_requests_project_number"),
        Index("idx_prs_project", "project_id"),
        Index("idx_prs_issue", "issue_id"),
        Index("idx_prs_state", "state"),
        Index("idx_prs_agent", "created_by_agent_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    branch_from: Mapped[str] = mapped_column(String(200), nullable=False)
    branch_to: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", server_default="open"
    )
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    review_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    test_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    issue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("github_issues.id"), nullable=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True
    )
    created_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    github_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="pull_requests")
    issue: Mapped["GithubIssue | None"] = relationship(back_populates="pull_requests")
    created_by_agent: Mapped["Agent | None"] = relationship()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'testing', 'review', 'completed', 'failed')",
            name="ck_tasks_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_tasks_priority",
        ),
        Index("idx_tasks_project", "project_id"),
        Index("idx_tasks_agent", "assigned_to_agent_id"),
        Index("idx_tasks_status_priority", "status", "priority"),
        Index("idx_tasks_issue", "issue_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    priority: Mapped[str] = mapped_column(String(10), default="medium", server_default="medium")
    assigned_to_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    issue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("github_issues.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    pr_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pull_requests.id", ondelete="SET NULL"), nullable=True
    )
    definition_of_done: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="tasks")
    assigned_to_agent: Mapped["Agent | None"] = relationship(back_populates="tasks_assigned")
    issue: Mapped["GithubIssue | None"] = relationship(back_populates="tasks")
    pr: Mapped["PullRequest | None"] = relationship()


# ---------------------------------------------------------------------------
# Token Usage
# ---------------------------------------------------------------------------
class TokenUsage(Base):
    __tablename__ = "token_usage"
    __table_args__ = (
        Index("idx_token_usage_timestamp", "timestamp"),
        Index("idx_token_usage_agent", "agent_id"),
        Index("idx_token_usage_project", "project_id"),
        Index("idx_token_usage_conversation", "conversation_id"),
        Index("idx_token_usage_date", "usage_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    agent_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=0, server_default="0"
    )
    request_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    was_cached: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


# ---------------------------------------------------------------------------
# Budget Limits
# ---------------------------------------------------------------------------
class BudgetLimit(Base):
    __tablename__ = "budget_limits"
    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('global', 'project', 'agent', 'agent_type')",
            name="ck_budget_limits_scope_type",
        ),
        CheckConstraint(
            "period IN ('daily', 'weekly', 'monthly')",
            name="ck_budget_limits_period",
        ),
        CheckConstraint(
            "alert_threshold > 0 AND alert_threshold <= 1.0",
            name="ck_budget_limits_alert_threshold",
        ),
        CheckConstraint(
            "action_on_exceed IN ('warn', 'block')",
            name="ck_budget_limits_action",
        ),
        Index("idx_budget_scope", "scope_type", "scope_id"),
        Index("idx_budget_agent_type", "scope_type", "scope_agent_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    scope_agent_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    alert_threshold: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("0.80"), server_default="0.80"
    )
    action_on_exceed: Mapped[str] = mapped_column(String(20), default="warn", server_default="warn")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="ck_notifications_severity",
        ),
        Index("idx_notifications_user", "user_id"),
        Index("idx_notifications_read", "user_id", "is_read"),
        Index("idx_notifications_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="info", server_default="info")
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sent_telegram: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sent_email: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="notifications")


# ---------------------------------------------------------------------------
# Agent Memory
# ---------------------------------------------------------------------------
class AgentMemory(Base):
    __tablename__ = "agent_memory"
    __table_args__ = (
        UniqueConstraint("agent_id", "project_id", "category", "key", name="uq_agent_memory_key"),
        CheckConstraint(
            "importance BETWEEN 1 AND 10",
            name="ck_agent_memory_importance",
        ),
        Index("idx_agent_memory_agent", "agent_id"),
        Index("idx_agent_memory_project", "project_id"),
        Index("idx_agent_memory_expires", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    importance: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="memories")


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------
class Webhook(Base):
    __tablename__ = "webhooks"
    __table_args__ = (
        Index("idx_webhooks_project", "project_id"),
        Index("idx_webhooks_processed", "processed"),
        Index("idx_webhooks_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_retries: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="webhooks")
