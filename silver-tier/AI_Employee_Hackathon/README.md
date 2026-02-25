# Personal AI Employee

> A "Digital FTE" - an autonomous AI agent that proactively manages personal and business affairs 24/7 using Claude Code as the executor and Obsidian as the management dashboard.

## Overview

The Personal AI Employee is an autonomous agent system that:

- **Monitors** your email, calendar, and other data sources (Perception)
- **Analyzes** incoming items and creates action plans (Reasoning)
- **Executes** approved actions like sending emails or scheduling (Action)

All while keeping you in control through a Human-in-the-Loop approval workflow.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   PERCEPTION    │────▶│    REASONING    │────▶│     ACTION      │
│    (Watchers)   │     │  (Claude Code)  │     │  (MCP Servers)  │
│                 │     │                 │     │                 │
│ - Email         │     │ - Read vault    │     │ - Send email    │
│ - Calendar      │     │ - Analyze       │     │ - Post social   │
│ - Social        │     │ - Create plans  │     │ - Make payments │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
   /vault/Inbox          /vault/Plans           /vault/Done
   /vault/Needs_Action   /vault/Pending_Approval
                         /vault/Approved
```

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- [Obsidian](https://obsidian.md/) (for viewing the vault)
- Claude Code CLI

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd AI_Employee_Hackathon
   ```

2. **Install dependencies with uv:**
   ```bash
   uv sync
   ```

3. **Copy environment template:**
   ```bash
   cp config/.env.example .env
   ```

4. **Configure your credentials in `.env`:**
   - Set up Gmail API credentials (see [Gmail Setup](#gmail-setup))
   - Keep `DEV_MODE=true` during development!

5. **Open the vault in Obsidian:**
   - Open Obsidian
   - Open folder as vault: `./vault`

6. **Customize your AI Employee:**
   - Edit `vault/Company_Handbook.md` with your preferences
   - Edit `vault/Business_Goals.md` with your objectives

### Gmail Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials and save as `config/credentials.json`
6. Add Client ID and Secret to your `.env` file

## Project Structure

```
AI_Employee_Hackathon/
├── .claude/                # Claude Code configuration
├── .specify/               # Spec-Kit Plus templates
├── skills/                 # AI Employee skills (SKILL.md files)
├── backend/
│   ├── watchers/           # Data source monitors
│   ├── mcp_servers/        # Action executors
│   ├── orchestrator/       # Main coordination logic
│   └── utils/              # Shared utilities
├── vault/                  # Obsidian vault (your dashboard)
│   ├── Dashboard.md        # Main status view
│   ├── Company_Handbook.md # Your preferences & rules
│   ├── Business_Goals.md   # Current objectives
│   ├── Inbox/              # Raw incoming items
│   ├── Needs_Action/       # Items requiring AI processing
│   ├── Plans/              # AI-generated action plans
│   ├── Pending_Approval/   # Awaiting your approval
│   ├── Approved/           # Ready for execution
│   ├── Rejected/           # Declined actions
│   ├── Done/               # Completed actions
│   ├── Logs/               # System logs
│   ├── Briefings/          # Daily CEO briefings
│   └── Accounting/         # Financial records
├── config/
│   ├── .env.example        # Environment template
│   ├── mcp.json            # MCP server configuration
│   └── rate_limits.json    # Rate limiting settings
├── scripts/                # Utility scripts
├── docs/                   # Documentation
└── tests/                  # Test suite
```

## Safety Features

### DEV_MODE (Default: ON)

When `DEV_MODE=true`:
- No real emails are sent
- No real payments are processed
- No real social media posts are made
- All actions are logged for review

**Always keep DEV_MODE=true during development!**

### Human-in-the-Loop (HITL)

Sensitive actions require your explicit approval:

1. AI creates a plan in `/vault/Plans/`
2. Plan moves to `/vault/Pending_Approval/`
3. You review and move to `/vault/Approved/` or `/vault/Rejected/`
4. Only approved actions are executed

**Never auto-approved:**
- Payments to new recipients
- Amounts over $100
- Bulk sends (>5 recipients)
- Social media posts
- Contracts/agreements

### Rate Limits

Built-in protection against runaway automation:
- Email: 10 sends/hour
- Payments: 3 transactions/hour
- Social: 5 posts/day/platform

Configure in `config/rate_limits.json`.

## Development

### Running Tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

### Type Checking

```bash
uv run mypy backend/
```

## Tier Progression

This project is designed for incremental development:

| Tier | Hours | Features |
|------|-------|----------|
| **Bronze** | 8-12 | Basic vault, 1 watcher, 2-3 skills |
| **Silver** | 20-30 | 2+ watchers, MCP actions, HITL workflow |
| **Gold** | 40+ | Odoo, social media, CEO briefings |
| **Platinum** | 60+ | Cloud deployment, mobile notifications |

See `.specify/memory/constitution.md` for full tier requirements.

## Architecture Principles

1. **Local-First**: All data stays in your Obsidian vault
2. **Privacy-Centric**: Credentials in `.env`, never in code
3. **Separation of Concerns**: Perception → Reasoning → Action
4. **Skills as First-Class Citizens**: All AI capabilities are modular skills
5. **Human-in-the-Loop**: You approve sensitive actions
6. **Fail-Safe**: DEV_MODE prevents accidental real actions

## Contributing

See `.specify/memory/constitution.md` for development principles and coding standards.

## License

MIT

---

Built for the Personal AI Employee Hackathon
