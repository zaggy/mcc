# Database Schema

## Overview

PostgreSQL database with SQLAlchemy 2.0 ORM.

**MVP Note:** The MVP uses SQLite. SQLAlchemy handles most differences, but avoid
PostgreSQL-specific features (JSONB, gen_random_uuid()) in application code. Use
SQLAlchemy's `Uuid` type and `JSON` type which adapt to both backends. Functional
indexes (e.g., `DATE(timestamp)`) are not supported in SQLite — use a separate
`date` column instead where needed.

## Tables

### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_2fa_enabled BOOLEAN DEFAULT FALSE,
    totp_secret VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    telegram_chat_id BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Note: UNIQUE constraints on username and email already create implicit indexes.
-- No additional indexes needed for these columns.
```

### projects
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    github_repo VARCHAR(255) NOT NULL,
    github_app_id VARCHAR(100),
    github_installation_id VARCHAR(100),
    local_path VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_github ON projects(github_repo);
```

### agents
```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('orchestrator', 'architect', 'coder', 'tester', 'reviewer')),
    model_config JSONB NOT NULL DEFAULT '{}',
    system_prompt TEXT,
    rules_file_path VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_agents_project ON agents(project_id);
CREATE INDEX idx_agents_type ON agents(type);
```

### conversations
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200),
    type VARCHAR(20) NOT NULL CHECK (type IN ('issue', 'general', 'task', 'review')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'archived')),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    -- Issue link is stored on github_issues.conversation_id (not here) to avoid circular FK.
    created_by_user_id UUID REFERENCES users(id),
    created_by_agent_id UUID REFERENCES agents(id),
    -- At least one of created_by_user_id or created_by_agent_id should be set.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_conversations_project ON conversations(project_id);
CREATE INDEX idx_conversations_status ON conversations(status);
```

### conversation_participants
```sql
CREATE TABLE conversation_participants (
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (conversation_id, agent_id)
);
```

### messages
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    author_type VARCHAR(20) NOT NULL CHECK (author_type IN ('user', 'agent')),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    content_formatted TEXT,
    reply_to_id UUID REFERENCES messages(id),
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0,
    model_used VARCHAR(100),
    is_edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX idx_messages_agent ON messages(agent_id);
```

### github_issues
```sql
CREATE TABLE github_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id BIGINT UNIQUE NOT NULL,
    number INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    body TEXT,
    state VARCHAR(20) NOT NULL DEFAULT 'open',
    labels JSONB DEFAULT '[]',
    assignee VARCHAR(100),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    github_created_at TIMESTAMP WITH TIME ZONE,
    github_updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(project_id, number)
);

CREATE INDEX idx_issues_project ON github_issues(project_id);
CREATE INDEX idx_issues_state ON github_issues(state);
CREATE INDEX idx_issues_conversation ON github_issues(conversation_id);
```

### pull_requests
```sql
CREATE TABLE pull_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id BIGINT UNIQUE NOT NULL,
    number INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    body TEXT,
    branch_from VARCHAR(200) NOT NULL,
    branch_to VARCHAR(200) NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'open',
    is_draft BOOLEAN DEFAULT FALSE,
    review_status VARCHAR(20),
    test_status VARCHAR(20),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    issue_id UUID REFERENCES github_issues(id),
    conversation_id UUID REFERENCES conversations(id),
    created_by_agent_id UUID REFERENCES agents(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    merged_at TIMESTAMP WITH TIME ZONE,
    github_created_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(project_id, number)
);

CREATE INDEX idx_prs_project ON pull_requests(project_id);
CREATE INDEX idx_prs_issue ON pull_requests(issue_id);
CREATE INDEX idx_prs_state ON pull_requests(state);
CREATE INDEX idx_prs_agent ON pull_requests(created_by_agent_id);
```

### tasks
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(300) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'testing', 'review', 'completed', 'failed')),
    priority VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    assigned_to_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    issue_id UUID REFERENCES github_issues(id) ON DELETE SET NULL,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    pr_id UUID REFERENCES pull_requests(id) ON DELETE SET NULL,
    definition_of_done TEXT,
    total_tokens_used INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10,6) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_agent ON tasks(assigned_to_agent_id);
CREATE INDEX idx_tasks_status_priority ON tasks(status, priority);
CREATE INDEX idx_tasks_issue ON tasks(issue_id);
```

### token_usage
```sql
CREATE TABLE token_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Usage date (denormalized from timestamp for indexing; works on both PG and SQLite).
    usage_date DATE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    agent_type VARCHAR(20),
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    model VARCHAR(100) NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cost_usd DECIMAL(10,6) NOT NULL DEFAULT 0,
    request_duration_ms INTEGER,
    was_cached BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_token_usage_timestamp ON token_usage(timestamp);
CREATE INDEX idx_token_usage_agent ON token_usage(agent_id);
CREATE INDEX idx_token_usage_project ON token_usage(project_id);
CREATE INDEX idx_token_usage_conversation ON token_usage(conversation_id);
CREATE INDEX idx_token_usage_date ON token_usage(usage_date);
```

### budget_limits
```sql
CREATE TABLE budget_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    scope_type VARCHAR(20) NOT NULL CHECK (scope_type IN ('global', 'project', 'agent', 'agent_type')),
    -- UUID for project/agent scopes, NULL for global.
    scope_id UUID,
    -- For agent_type scope, stores the type name (e.g., 'coder'). NULL otherwise.
    scope_agent_type VARCHAR(20),
    amount_usd DECIMAL(10,2) NOT NULL,
    period VARCHAR(20) NOT NULL CHECK (period IN ('daily', 'weekly', 'monthly')),
    alert_threshold DECIMAL(3,2) DEFAULT 0.80 CHECK (alert_threshold > 0 AND alert_threshold <= 1.0),
    action_on_exceed VARCHAR(20) DEFAULT 'warn' CHECK (action_on_exceed IN ('warn', 'block')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_budget_scope ON budget_limits(scope_type, scope_id);
CREATE INDEX idx_budget_agent_type ON budget_limits(scope_type, scope_agent_type);
```

### notifications
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'critical')),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id),
    agent_id UUID REFERENCES agents(id),
    is_read BOOLEAN DEFAULT FALSE,
    sent_telegram BOOLEAN DEFAULT FALSE,
    sent_email BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at);
```

### agent_memory
```sql
CREATE TABLE agent_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id),
    category VARCHAR(50) NOT NULL,
    key VARCHAR(200) NOT NULL,
    value JSONB NOT NULL,
    importance INTEGER DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_id, project_id, category, key)
);

CREATE INDEX idx_agent_memory_agent ON agent_memory(agent_id);
CREATE INDEX idx_agent_memory_project ON agent_memory(project_id);
CREATE INDEX idx_agent_memory_expires ON agent_memory(expires_at);
```

### webhooks
```sql
CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_webhooks_project ON webhooks(project_id);
CREATE INDEX idx_webhooks_processed ON webhooks(processed);
CREATE INDEX idx_webhooks_created ON webhooks(created_at);
```

## Entity Relationships

```
users ||--o{ projects : owns
users ||--o{ conversations : creates
users ||--o{ notifications : receives

projects ||--o{ agents : has
projects ||--o{ conversations : contains
projects ||--o{ github_issues : tracks
projects ||--o{ pull_requests : contains
projects ||--o{ tasks : manages

agents ||--o{ messages : sends
agents ||--o{ tasks : assigned_to
agents ||--o{ agent_memory : stores

conversations ||--o{ messages : contains
conversations ||--o{ conversation_participants : has
-- Issue→Conversation link is on github_issues.conversation_id (one direction only)

github_issues ||--o{ pull_requests : resolves
github_issues ||--o{ tasks : generates
github_issues ||--o| conversations : has

pull_requests ||--o| tasks : implements
pull_requests |o--o{ token_usage : generates

token_usage }o--|| agents : tracks
token_usage }o--|| projects : tracks
token_usage }o--|| conversations : tracks

budget_limits }o--o| projects : constrains
budget_limits }o--o| agents : constrains
```

## Key Indexes for Performance

**Note:** PostgreSQL does NOT automatically create indexes on foreign key columns
(only on PRIMARY KEY and UNIQUE constraints). All FK columns that are used in
lookups or joins must be explicitly indexed. The indexes above cover the important
FK columns.

Key composite indexes:
- `messages(conversation_id, created_at)` for chronological chat loading
- `tasks(status, priority)` for task queue ordering
- `notifications(user_id, is_read)` for inbox queries
- `token_usage(usage_date)` for daily aggregation (replaces functional DATE() index for SQLite compatibility)

## JSONB Usage

- `agents.model_config`: { model, temperature, max_tokens, ... }
- `github_issues.labels`: [ "bug", "urgent", ... ]
- `token_usage.metadata`: { request_id, cached, ... }
- `notifications.metadata`: { related_entity_type, related_entity_id, ... }
