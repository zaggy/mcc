# API Specification

## Base URL

```
https://mcc.lymar.site/api/v1
```

## Authentication

All endpoints require Bearer token in Authorization header:
```
Authorization: Bearer <jwt_token>
```

## REST Endpoints

### Authentication

#### POST /auth/login
Login with credentials.

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "requires_2fa": false
}
```

#### POST /auth/2fa/verify
Verify 2FA code.

**Request:**
```json
{
  "temp_token": "string",
  "code": "123456"
}
```

**Response:** Same as login.

#### POST /auth/refresh
Refresh access token.

**Request:**
```json
{
  "refresh_token": "string"
}
```

### Projects

#### GET /projects
List all projects.

**Query params:**
- `page`: integer (default: 1)
- `limit`: integer (default: 20, max: 100)
- `is_active`: boolean

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "github_repo": "owner/repo",
      "is_active": true,
      "created_at": "2026-02-12T00:00:00Z",
      "stats": {
        "open_issues": 5,
        "active_conversations": 2,
        "today_cost": 12.50
      }
    }
  ],
  "total": 10,
  "page": 1,
  "pages": 1
}
```

#### POST /projects
Create new project.

**Request:**
```json
{
  "name": "My Project",
  "description": "string",
  "github_repo": "owner/repo",
  "github_app_id": "string",
  "github_installation_id": "string"
}
```

#### GET /projects/{id}
Get project details.

#### PATCH /projects/{id}
Update project.

#### DELETE /projects/{id}
Delete project and all related data.

### Agents

#### GET /projects/{id}/agents
List agents for project.

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Senior Architect",
      "type": "architect",
      "model_config": {
        "model": "anthropic/claude-3.5-sonnet",
        "temperature": 0.2,
        "max_tokens": 4096
      },
      "is_active": true,
      "stats": {
        "messages_today": 15,
        "cost_today": 5.20
      }
    }
  ]
}
```

#### POST /projects/{id}/agents
Create agent.

**Request:**
```json
{
  "name": "string",
  "type": "architect|coder|tester|reviewer|orchestrator",
  "model_config": {
    "model": "string",
    "temperature": 0.0-2.0,
    "max_tokens": 100-128000
  },
  "system_prompt": "string",
  "rules_file_path": "string"
}
```

#### PATCH /projects/{project_id}/agents/{id}
Update agent configuration.

#### POST /projects/{project_id}/agents/{id}/reset
Reset agent memory/conversations.

### Conversations

#### GET /projects/{id}/conversations
List conversations.

**Query params:**
- `type`: issue|general|task|review
- `status`: active|paused|completed

#### POST /projects/{id}/conversations
Create conversation.

**Request:**
```json
{
  "title": "string",
  "type": "general",
  "agent_ids": ["uuid", "uuid"],
  "issue_id": "uuid"
}
```

#### GET /projects/{project_id}/conversations/{id}
Get conversation with messages.

**Query params:**
- `before`: message_id (cursor-based pagination)
- `limit`: integer (default: 50)

**Response:**
```json
{
  "id": "uuid",
  "title": "string",
  "type": "issue",
  "status": "active",
  "agents": [...],
  "messages": [
    {
      "id": "uuid",
      "author_type": "agent",
      "agent": { "id": "uuid", "name": "string", "type": "architect" },
      "content": "string",
      "tokens_in": 1500,
      "tokens_out": 800,
      "cost_usd": 0.045,
      "created_at": "2026-02-12T00:00:00Z",
      "reply_to": null
    }
  ],
  "has_more": true
}
```

#### POST /projects/{project_id}/conversations/{id}/messages
Send message to conversation.

**Request:**
```json
{
  "content": "string",
  "reply_to": "uuid|null"
}
```

#### POST /projects/{project_id}/conversations/{id}/pause
Pause all agent activity.

#### POST /projects/{project_id}/conversations/{id}/resume
Resume agent activity.

### Issues

#### GET /projects/{id}/issues
List GitHub issues.

**Query params:**
- `state`: open|closed|all
- `label`: string

#### POST /projects/{project_id}/issues/{id}/start
Start working on issue (assigns to Architect).

#### GET /projects/{project_id}/issues/{id}/tasks
Get tasks created from issue.

### Tasks

#### GET /projects/{project_id}/tasks
List tasks for project.

**Query params:**
- `status`: pending|in_progress|testing|review|completed|failed
- `assigned_to`: agent_id
- `issue_id`: uuid

#### POST /projects/{project_id}/tasks
Create task manually.

**Request:**
```json
{
  "title": "string",
  "description": "string",
  "priority": "low|medium|high|urgent",
  "issue_id": "uuid|null",
  "assigned_to_agent_id": "uuid|null",
  "definition_of_done": "string"
}
```

#### GET /projects/{project_id}/tasks/{id}
Get task details.

**Response:**
```json
{
  "id": "uuid",
  "title": "string",
  "description": "string",
  "status": "in_progress",
  "priority": "high",
  "assigned_to": { "id": "uuid", "name": "string", "type": "coder" },
  "issue": { "id": "uuid", "number": 5, "title": "string" },
  "pr": { "id": "uuid", "number": 12, "status": "open" },
  "definition_of_done": "string",
  "progress": 45,
  "created_at": "2026-02-12T00:00:00Z"
}
```

#### POST /projects/{project_id}/tasks/{id}/assign
Assign task to agent.

#### POST /projects/{project_id}/tasks/{id}/complete
Mark task as complete.

### Pull Requests

#### GET /projects/{id}/pull-requests
List PRs.

#### POST /projects/{project_id}/pull-requests/{id}/approve
Approve PR (triggers merge if all checks pass).

#### POST /projects/{project_id}/pull-requests/{id}/reject
Reject PR with feedback.

### Budget & Analytics

#### GET /budget/summary
Get budget overview.

**Response:**
```json
{
  "today": { "spent": 12.50, "limit": 50.00, "percentage": 0.25 },
  "week": { "spent": 89.20, "limit": 300.00, "percentage": 0.30 },
  "month": { "spent": 450.00, "limit": 1000.00, "percentage": 0.45 },
  "alerts": [
    {
      "type": "warning",
      "message": "Project 'X' at 85% of daily limit"
    }
  ]
}
```

#### GET /budget/by-project
Spending by project.

#### GET /budget/by-agent
Spending by agent.

#### GET /budget/timeline
Daily spending over time.

**Query params:**
- `start_date`: YYYY-MM-DD
- `end_date`: YYYY-MM-DD
- `granularity`: day|week|month

#### GET /analytics/agents
Agent performance metrics.

**Response:**
```json
{
  "agents": [
    {
      "id": "uuid",
      "name": "string",
      "type": "coder",
      "metrics": {
        "total_messages": 150,
        "total_cost": 45.20,
        "avg_cost_per_message": 0.30,
        "tasks_completed": 12,
        "success_rate": 0.95
      }
    }
  ]
}
```

### Budget Limits

#### GET /budget/limits
List all budget limits.

#### POST /budget/limits
Create limit.

**Request:**
```json
{
  "name": "Daily Global Limit",
  "scope_type": "global",
  "scope_id": null,
  "amount_usd": 50.00,
  "period": "daily",
  "alert_threshold": 0.80,
  "action_on_exceed": "warn"
}
```

#### PATCH /budget/limits/{id}
Update limit.

#### DELETE /budget/limits/{id}
Delete limit.

### Notifications

#### GET /notifications
List notifications.

**Query params:**
- `is_read`: boolean
- `severity`: info|warning|critical
- `limit`: integer

#### POST /notifications/{id}/read
Mark as read.

#### POST /notifications/read-all
Mark all as read.

### Emergency

#### POST /emergency/pause-all
EMERGENCY: Pause all agents system-wide.

**Response:**
```json
{
  "paused_agents": 5,
  "active_conversations": 2,
  "message": "All agents paused. Manual resume required."
}
```

#### POST /emergency/resume-all
Resume all agents.

## WebSocket API

### Connection

```javascript
const socket = io('wss://mcc.lymar.site', {
  auth: { token: 'jwt_token' }
});
```

### Client → Server Events

#### join_conversation
Subscribe to conversation updates.

```javascript
socket.emit('join_conversation', { conversation_id: 'uuid' });
```

#### leave_conversation
Unsubscribe.

```javascript
socket.emit('leave_conversation', { conversation_id: 'uuid' });
```

#### send_message
Send message (alternative to REST).

```javascript
socket.emit('send_message', {
  conversation_id: 'uuid',
  content: 'Hello agents',
  reply_to: 'uuid' // optional
});
```

#### typing_indicator
Show typing status.

```javascript
socket.emit('typing', { conversation_id: 'uuid', is_typing: true });
```

### Server → Client Events

#### message
New message in conversation.

```javascript
socket.on('message', (data) => {
  // data: same as REST message object
});
```

#### agent_status
Agent status changed.

```javascript
socket.on('agent_status', {
  agent_id: 'uuid',
  status: 'idle|working|error',
  current_task: { id: 'uuid', title: 'string' },
  timestamp: '2026-02-12T00:00:00Z'
});
```

#### agent_typing
Agent is typing.

```javascript
socket.on('agent_typing', {
  conversation_id: 'uuid',
  agent_id: 'uuid',
  is_typing: true
});
```

#### task_progress
Task progress update.

```javascript
socket.on('task_progress', {
  task_id: 'uuid',
  progress: 45, // percentage
  status: 'in_progress',
  message: 'Compiling tests...'
});
```

#### budget_alert
Budget warning.

```javascript
socket.on('budget_alert', {
  level: 'warning|critical',
  scope: { type: 'project|agent', id: 'uuid', name: 'string' },
  current: 42.50,
  limit: 50.00,
  percentage: 0.85,
  message: 'Project X at 85% of daily limit'
});
```

#### emergency_pause
System-wide pause triggered.

```javascript
socket.on('emergency_pause', {
  triggered_by: 'user|system',
  reason: 'Budget limit exceeded',
  timestamp: '2026-02-12T00:00:00Z'
});
```

#### error
Error notification.

```javascript
socket.on('error', {
  code: 'string',
  message: 'string',
  details: {}
});
```

## GitHub Webhooks

Endpoint: `POST /webhooks/github`

Handles events:
- `issues` - created, edited, closed, reopened
- `issue_comment` - created, edited
- `pull_request` - opened, edited, closed, reopened, synchronized
- `pull_request_review` - submitted, edited
- `push` - branch updates

All events authenticated via GitHub signature verification.

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Project not found",
    "details": {},
    "request_id": "uuid"
  }
}
```

Common codes:
- `UNAUTHORIZED` - Invalid or expired token
- `FORBIDDEN` - Insufficient permissions
- `RESOURCE_NOT_FOUND` - Entity doesn't exist
- `VALIDATION_ERROR` - Invalid input data
- `BUDGET_EXCEEDED` - Spending limit reached
- `AGENT_BUSY` - Agent already working on task
- `GITHUB_API_ERROR` - GitHub API failure

## Rate Limits

- Authenticated: 100 requests per minute per IP
- WebSocket: 100 messages per minute per connection
- Budget checks: Unlimited

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1707782400
```

## Pagination

All list endpoints use offset-based pagination:

**Query params:**
- `page`: integer (default: 1)
- `limit`: integer (default: 20, max: 100)

**Response:**
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "pages": 10
}
```

**Exception:** Message lists within conversations use cursor-based pagination
(using `before` message_id) since messages are append-heavy and offset pagination
would be unstable as new messages arrive:
```json
{
  "items": [...],
  "has_more": true
}
```
