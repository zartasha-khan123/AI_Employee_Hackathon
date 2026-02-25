# AI Employee - Silver Tier Quick Start

**Status:** Silver Tier Complete ✅
**Date:** 2026-02-15

## What's New in Silver Tier

- ✅ **Google Calendar Watcher** - Monitors upcoming events requiring preparation
- ✅ **Orchestrator** - Automated reasoning and plan generation
- ✅ **MCP Email Server** - Send emails with safety controls
- ✅ **HITL Approval Workflow** - Human oversight for sensitive actions
- ✅ **Process Management** - Unified service management

## Quick Start (5 Minutes)

### 1. Setup OAuth Tokens

```bash
# Gmail (if not already done)
uv run python skills/gmail-watcher/scripts/setup_gmail_oauth.py

# Calendar
uv run python skills/calendar-watcher/scripts/setup_calendar_oauth.py
```

### 2. Configure Email (Optional)

Edit `config/.env`:
```bash
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
ALLOWED_RECIPIENTS=test@example.com
```

### 3. Start All Services

```powershell
.\scripts\start.ps1
```

### 4. Check Status

```powershell
.\scripts\status.ps1
```

## Test the Workflow

### End-to-End Test

1. **Send yourself a test email** (Gmail watcher will detect it)
2. **Check action file created:** `vault/Needs_Action/email-*.md`
3. **Orchestrator creates plan:** `vault/Plans/plan-*.md`
4. **Plan moved to approval:** `vault/Pending_Approval/plan-*.md`
5. **Approve the plan:**
   ```bash
   python scripts/approve.py plan-email-test-20260215.md
   ```
6. **Check execution result:** `vault/Done/plan-*.md`

### Component Tests

```bash
# Test Gmail watcher (single check)
uv run python backend/watchers/gmail_watcher.py --once

# Test Calendar watcher (single check)
uv run python backend/watchers/calendar_watcher.py --once

# Test Orchestrator (single cycle)
uv run python backend/orchestrator/main.py --once

# Test MCP Email Server
uv run python -m backend.mcp_servers.email_server.server
# Then send JSON request via stdin
```

## Architecture

```
Gmail Watcher ──┐
                ├──> vault/Needs_Action/ ──> Orchestrator ──> vault/Plans/
Calendar Watcher┘                                │
                                                 ├──> vault/Pending_Approval/
                                                 │         │
                                                 │    [HUMAN APPROVAL]
                                                 │         │
                                                 ├──> vault/Approved/
                                                 │         │
                                                 └──> MCP Email Server
                                                           │
                                                      vault/Done/
```

## Safety Features

- **DEV_MODE=true** (default) - Simulates all actions, no real sends
- **DRY_RUN=true** (default) - Logs without executing
- **Approval Required** - Sensitive actions need human approval
- **Rate Limiting** - 10 emails/hour, 50/day
- **Content Scanning** - Blocks passwords, credit cards, SSN
- **Recipient Allowlist** - Only approved recipients in production

## Commands

```powershell
# Service Management
.\scripts\start.ps1          # Start all services
.\scripts\stop.ps1           # Stop all services
.\scripts\status.ps1         # Check status

# Approval Workflow
python scripts/approve.py <plan-file>
python scripts/reject.py <plan-file> "<reason>"

# View Vault
ls vault/Needs_Action/      # Action files from watchers
ls vault/Pending_Approval/  # Plans awaiting approval
ls vault/Approved/           # Approved plans
ls vault/Done/               # Completed actions
```

## Configuration Files

- `config/.env` - Environment variables (credentials, intervals)
- `config/gmail_config.json` - Gmail watcher settings
- `config/calendar_config.json` - Calendar watcher settings
- `config/rate_limits.json` - Rate limiting rules
- `config/mcp.json` - MCP server configuration

## Documentation

- **Skills:** `skills/*/SKILL.md` - Component documentation
- **Briefings:** `vault/Briefings/silver-tier-completion.md` - Implementation summary
- **Constitution:** `.specify/memory/constitution.md` - Architecture principles

## Troubleshooting

### Services won't start
```powershell
# Check virtual environment
uv venv

# Check .env file exists
ls config/.env

# Check OAuth tokens
ls config/token.json
ls config/calendar_token.json
```

### No action files created
```bash
# Check watcher logs
tail -f vault/Logs/actions/*.jsonl

# Test watcher manually
uv run python backend/watchers/gmail_watcher.py --once
```

### Plans not being approved
```bash
# List pending approvals
ls vault/Pending_Approval/

# Approve manually
python scripts/approve.py <filename>
```

## Next Steps

1. **Test end-to-end workflow** with real email
2. **Adjust approval thresholds** in `backend/orchestrator/plan_generator.py`
3. **Configure email sending** (set DEV_MODE=false for production)
4. **Monitor logs** in `vault/Logs/`
5. **Review completed actions** in `vault/Done/`

## Production Deployment

To use in production (real actions):

1. Set `DEV_MODE=false` in `config/.env`
2. Set `DRY_RUN=false` in `config/.env`
3. Configure `SMTP_USER` and `SMTP_PASSWORD`
4. Set `ALLOWED_RECIPIENTS` to approved emails
5. Test with low-risk actions first
6. Monitor `vault/Logs/` closely

## Support

- **Issues:** Check `vault/Logs/errors/`
- **Documentation:** `skills/*/SKILL.md`
- **Architecture:** `.specify/memory/constitution.md`

---

**Silver Tier Complete** ✅ | **Ready for Gold Tier** 🎯
