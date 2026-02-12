# Technical Architecture Document

## System Overview

Mission Control Center (MCC) is a multi-agent AI software development platform that orchestrates a virtual software company through a web-based interface.

## High-Level Architecture

### Monolithic Architecture with Modular Design

```
┌─────────────────────────────────────────────────────────────┐
│                     Nginx / Caddy                          │
│                     (Reverse Proxy)                         │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  React SPA   │   │  FastAPI     │   │  WebSocket   │
│  (Frontend)  │◄──│  (Backend)   │◄──│  Server      │
└──────────────┘   └──────────────┘   └──────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  PostgreSQL  │   │  Redis       │   │  Local Git   │
│  (Data)      │   │  (Queue/     │   │  Worktrees   │
└──────────────┘   │  Cache)      │   └──────────────┘
                   └──────────────┘
                           │
                           ▼
                   ┌──────────────┐
                   │  Celery      │
                   │  Workers     │
                   └──────────────┘
```

## Component Details

### Frontend (React SPA)

**Stack:**
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS + shadcn/ui
- Zustand (state management)
- React Query (server state)
- Socket.io-client (WebSocket)
- Recharts (analytics)

**Key Features:**
- Dark theme by default
- Discord-inspired chat interface
- Mobile-responsive design
- Real-time updates via WebSocket

**Routes:**
- `/login` - Authentication
- `/` - Dashboard
- `/projects` - Project list
- `/projects/:id` - Project detail with agent chats
- `/agents` - Agent configuration
- `/budget` - Budget & analytics
- `/settings` - System settings

### Backend (FastAPI)

**Stack:**
- Python 3.12
- FastAPI (web framework)
- SQLAlchemy 2.0 (ORM)
- Alembic (migrations)
- Pydantic (validation)
- Celery (background tasks)
- Socket.io (WebSocket)

**Modules:**
```
app/
├── api/                    # API routes
│   ├── auth.py            # Authentication
│   ├── projects.py        # Project management
│   ├── agents.py          # Agent CRUD & config
│   ├── conversations.py   # Chat management
│   ├── issues.py          # GitHub issues
│   ├── budget.py          # Budget tracking
│   └── websocket.py       # WebSocket handlers
├── core/                   # Core functionality
│   ├── config.py          # Settings
│   ├── security.py        # JWT, 2FA
│   └── exceptions.py      # Error handling
├── db/                     # Database
│   ├── models.py          # SQLAlchemy models
│   └── session.py         # DB session
├── services/               # Business logic
│   ├── agent_service.py   # Agent orchestration
│   ├── github_service.py  # GitHub integration
│   ├── openrouter.py      # LLM API
│   ├── budget_service.py  # Budget tracking
│   └── notification.py    # Telegram alerts
├── agents/                 # Agent implementations
│   ├── base.py            # Base agent class
│   ├── orchestrator.py    # Orchestrator agent
│   ├── architect.py       # Architect agent
│   ├── coder.py           # Coder agent
│   ├── tester.py          # Tester agent
│   └── reviewer.py        # Reviewer agent
├── models/                 # Pydantic models
└── main.py                # Application entry
```

### Database (PostgreSQL)

**Key Tables:**
- `users` - System users with 2FA
- `projects` - GitHub repository links
- `agents` - Agent configurations and AGENTS.md rules
- `conversations` - Chat threads
- `messages` - Individual messages with token tracking
- `github_issues` - Cached issue data
- `pull_requests` - PR tracking
- `token_usage` - Granular usage logging
- `budget_limits` - Spending limits
- `notifications` - Alert history

### Redis (Production only — not required for MVP)

**Usage:**
- Celery broker (production background tasks)
- Cache for GitHub API responses
- Rate limiting counters

### Background Task Processing

**MVP:** Use FastAPI background tasks (`BackgroundTasks`) and `asyncio` for
simple async work. This avoids requiring Redis + Celery infrastructure when using
SQLite.

**Production (with PostgreSQL + Redis):** Migrate to Celery workers with queues:
- `agent_tasks` - Agent execution
- `github_sync` - GitHub webhook processing
- `notifications` - Telegram/email alerts
- `budget_checks` - Periodic budget monitoring

### Local Git Worktrees

**Structure:**
```
/data/repos/
└── {project_id}/
    ├── main/              # Main branch checkout
    ├── agent_{agent_id}/  # Agent worktrees
    │   ├── architect/
    │   ├── coder_1/
    │   ├── coder_2/
    │   ├── tester/
    │   └── reviewer/
    └── temp/              # Temporary operations
```

## Agent Communication Flow

### Direct Agent Communication

```
┌─────────────┐     ┌─────────────┐
│  Architect  │◄───►│   Coder 1   │
└──────┬──────┘     └──────┬──────┘
       │                   │
       │    ┌─────────┐    │
       └───►│  User   │◄───┘
            │ (You/Me)│
            └────┬────┘
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│  Tester  │ │ Reviewer │ │ Coder 2  │
└──────────┘ └──────────┘ └──────────┘
```

### Communication Rules

1. **Orchestrator (You/Me)** can message any agent
2. **Architect** can message Coders, Tester, Reviewer
3. **Coders** can message Tester, Reviewer, Architect (for clarifications)
4. **Tester** can message Coders (bug reports), Reviewer, Architect
5. **Reviewer** can message Coders (feedback), Architect
6. **All conversations visible to User** in the UI
7. **User can intervene** at any point

## WebSocket Events

### Client → Server

```javascript
// Join conversation
{ type: "join_conversation", conversation_id: "uuid" }

// Send message
{ type: "send_message", conversation_id: "uuid", content: "text", reply_to: "uuid|null" }

// Create task/issue
{ type: "create_issue", project_id: "uuid", title: "...", description: "..." }

// Pause all agents
{ type: "emergency_pause" }
```

### Server → Client

```javascript
// New message
{ type: "message", data: { id, content, author, timestamp, tokens, cost } }

// Agent status
{ type: "agent_status", agent_id: "...", status: "idle|working|error", current_task: "..." }

// Budget alert
{ type: "budget_alert", level: "warning|critical", current: 0.85, limit: 1.0 }

// Task progress
{ type: "task_progress", task_id: "...", percent: 45, status: "..." }
```

## Agent Memory Architecture

### Orchestrator Memory
- Long-term: All projects, decisions, preferences
- Stored in: `conversations` table + AGENTS.md file

### Architect Memory
- Long-term: Project architecture decisions, patterns
- Stored in: `conversations` table + AGENTS.md file

### Other Agents (Coder, Tester, Reviewer)
- Short-term: Only current task context
- No persistence between tasks
- Fresh AGENTS.md loaded for each task

### AGENTS.md Files

Located in project root:
```
{project_root}/
├── .mcc/
│   ├── AGENTS.md           # Global rules
│   ├── orchestrator.md     # Orchestrator rules
│   ├── architect.md        # Architect rules
│   ├── coder.md            # Coder rules
│   ├── tester.md           # Tester rules
│   └── reviewer.md         # Reviewer rules
```

## GitHub Integration

### GitHub App Setup

**Permissions needed:**
- Repository: Read & Write
- Issues: Read & Write
- Pull requests: Read & Write
- Contents: Read & Write
- Metadata: Read

**Events to subscribe:**
- Issues
- Issue comment
- Pull request
- Pull request review
- Push

### Workflow Integration

```
1. GitHub Issue created (by User or Orchestrator)
   ↓
2. Webhook → MCC → Architect notified
   ↓
3. Architect analyzes → Creates technical spec
   ↓
4. MCC creates tasks → Assigns to Coders
   ↓
5. Coders create branches → Write code → Open PRs
   ↓
6. Tester validates → Reviewer reviews
   ↓
7. User approves → MCC merges PR
   ↓
8. CI/CD runs automatically (written by agents)
```

## Budget Control System

### Hierarchical Limits

```
Global Daily Limit
├── Project A (40%)
│   ├── Architect (20%)
│   ├── Coder 1 (40%)
│   ├── Coder 2 (40%)
├── Project B (60%)
```

### Enforcement Points

1. **Pre-flight check**: Before API call, verify limit
2. **Soft warning**: At 80% of any limit, notify but allow
3. **Hard stop**: At 100% of limit, block API calls
4. **Emergency pause**: Immediate stop all agents

### Tracking

Every API call logs:
```json
{
  "timestamp": "2026-02-11T12:00:00Z",
  "agent_id": "uuid",
  "agent_type": "coder",
  "model": "anthropic/claude-3.5-sonnet",
  "tokens_in": 1500,
  "tokens_out": 800,
  "cost_usd": 0.045,
  "conversation_id": "uuid",
  "project_id": "uuid",
  "task_id": "uuid"
}
```

## Security Considerations

### Authentication
- JWT with 15-minute expiry
- Refresh tokens with 7-day expiry
- 2FA with TOTP (Google Authenticator)

### API Security
- Rate limiting: 100 req/min per IP (see API_SPEC.md for details)
- GitHub tokens encrypted at rest (AES-256)
- OpenRouter key in environment only

### Agent Sandboxing (Future)
- Docker containers for code execution
- Network isolation
- Resource limits (CPU, memory, disk)
- No access to secrets/env vars

## Deployment Architecture

### Docker Compose (Development)

```yaml
services:
  postgres:
    image: postgres:15
    
  redis:
    image: redis:7
    
  backend:
    build: ./backend
    depends_on: [postgres, redis]
    
  frontend:
    build: ./frontend
    
  celery_worker:
    build: ./backend
    command: celery -A app.tasks worker
    depends_on: [postgres, redis]
    
  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
```

### Production (Future)
- Kubernetes with Helm charts
- PostgreSQL with read replicas
- Redis Cluster
- CDN for static assets

## API Rate Limits

### OpenRouter
- Track usage in real-time
- Backoff on 429 errors
- Queue system for retries

### GitHub API
- 5000 req/hour (authenticated)
- Aggressive caching (ETags)
- Conditional requests

## Error Handling

### Agent Failures
1. Retry with exponential backoff (3 attempts)
2. Escalate to User if persistent
3. Log detailed error context

### System Failures
1. Graceful degradation (disable non-essential features)
2. Emergency pause on critical errors
3. Telegram alert to user

## Next Steps

1. ✅ Define architecture (this document)
2. 🔄 Create database schema
3. ⏳ Define API specifications
4. ⏳ Create UI wireframes
5. ⏳ Set up project structure

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-11
