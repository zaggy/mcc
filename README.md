# 🚀 Mission Control Center (MCC)

**Your AI-Powered Software Company**

Mission Control Center is a multi-agent AI platform that orchestrates a virtual software development team. It manages specialized AI agents—Architect, Coders, Tester, and Code Reviewer—to deliver software projects through a structured workflow.

![Status](https://img.shields.io/badge/status-planning-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 🎯 Vision

Transform software development by creating an autonomous team of AI agents that can:
- Analyze requirements and create technical specifications
- Write production-ready code
- Test and validate implementations
- Review code for quality and security
- Deliver complete features through GitHub PRs

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Mission Control Center                   │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │Architect │  │ Coder 1  │  │ Coder 2  │  │  Tester  │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │             │             │           │
│       └─────────────┴─────────────┴─────────────┘           │
│                         │                                   │
│                   ┌─────┴─────┐                            │
│                   │ Code Reviewer │                         │
│                   └─────┬─────┘                            │
│                         │                                   │
│  ┌──────────────────────┴──────────────────────┐           │
│  │           GitHub Integration                │           │
│  │   Issues → PRs → Reviews → Merge → CI/CD   │           │
│  └─────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

- **Backend:** Python 3.12 + FastAPI
- **Frontend:** React 18 + TypeScript + Tailwind CSS
- **Database:** PostgreSQL (production) / SQLite (MVP)
- **LLM Provider:** OpenRouter API
- **Task Queue:** Celery + Redis
- **Container:** Docker + Docker Compose

## 📋 Features

### Core Features
- ✅ Multi-agent conversation system
- ✅ GitHub integration (Issues, PRs, Webhooks)
- ✅ Token usage tracking per agent/model
- ✅ Budget management with limits and alerts
- ✅ Real-time dashboard with analytics
- ✅ Agent model configuration (hot-swappable)

### Workflow
1. **Issue Creation** - You or the system creates a GitHub issue
2. **Planning** - Architect agent analyzes and creates technical spec
3. **Implementation** - Coder agents write code in feature branches
4. **Testing** - Tester agent validates against requirements
5. **Review** - Code Reviewer checks quality and best practices
6. **Merge** - You approve and merge the PR
7. **Deploy** - CI/CD takes over

## 📊 Budget & Analytics

Track every penny spent on AI agents:
- Real-time token usage per agent/project
- Cost breakdown by model and agent type
- Budget limits (global, per-project, per-agent)
- Email/notification alerts when thresholds are hit
- Historical reports and spending trends

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose
- GitHub account with API access
- OpenRouter API key
- Python 3.12+ (for local development)
- Node.js 20+ (for frontend development)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/zaggy/mission-control-center.git
cd mission-control-center

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Start with Docker Compose
docker-compose up -d

# Access the application
open http://localhost:3000
```

## 📖 Documentation

- [Project Plan](./PROJECT_PLAN.md) - Detailed roadmap and phases
- [API Documentation](./docs/API_SPEC.md) - API reference (coming soon)
- [Deployment Guide](./docs/DEPLOYMENT.md) - Production setup (coming soon)

## 🗺️ Roadmap

### Phase 1: Architecture & Design ✅
- Technical specifications
- Database schema design
- UI/UX wireframes
- API contracts

### Phase 2: Core Infrastructure
- Project bootstrap
- Database layer
- Authentication system
- Basic web interface

### Phase 3: Agent Core System
- OpenRouter integration
- Agent framework
- Specialized agent implementations
- Communication protocol

### Phase 4: GitHub Integration
- API integration
- Webhook system
- PR management

### Phase 5: Budget & Analytics
- Token tracking
- Budget management
- Analytics dashboard
- Notifications

### Phase 6: Workflow Automation
- Issue lifecycle management
- Task distribution
- Review & approval flow
- Orchestrator mode

### Phase 7: Advanced Features
- Sandbox environments
- Knowledge base
- Multi-project management
- External integrations

### Phase 8: Production
- Testing & QA
- Documentation
- Production deployment
- Security hardening

## 🤝 Contributing

This is a personal project, but suggestions and feedback are welcome through GitHub Issues.

## 📄 License

MIT License - see [LICENSE](./LICENSE) file for details.

## 🙏 Acknowledgments

- Built with love by [Anya](https://github.com/zaggy) and [Sergey](https://github.com/zaggy)
- Powered by [OpenRouter](https://openrouter.ai/)
- Inspired by the future of AI-assisted development

---

**Status:** 🚧 In Planning Phase

For detailed task breakdown, see [PROJECT_PLAN.md](./PROJECT_PLAN.md)
