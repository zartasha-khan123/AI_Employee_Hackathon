# Silver Tier Testing Guide

Quick tests to verify Silver Tier implementation.

## 1. Check Installation

```bash
# Verify all files exist
ls backend/watchers/calendar_watcher.py
ls backend/orchestrator/main.py
ls backend/mcp_servers/email_server/server.py
ls scripts/approve.py
ls scripts/start.ps1
```

## 2. Test Calendar Watcher

```bash
# Setup OAuth (first time only)
uv run python skills/calendar-watcher/scripts/setup_calendar_oauth.py

# Test single check
uv run python backend/watchers/calendar_watcher.py --once
```

Expected: "Check complete. Found X events requiring preparation."

## 3. Test Orchestrator

```bash
# Create test action file
cat > vault/Needs_Action/test-action.md << 'TESTEOF'
---
type: email
id: EMAIL_test123_20260215T143022
source: test
from: test@example.com
subject: Test Email
priority: low
status: pending
---

## Email Content
This is a test email for orchestrator testing.
TESTEOF

# Run orchestrator once
uv run python backend/orchestrator/main.py --once
```

Expected: Plan created in vault/Plans/

## 4. Test Approval Workflow

```bash
# List pending approvals
ls vault/Pending_Approval/

# Approve a plan
python scripts/approve.py plan-test-action-*.md

# Verify moved to Approved
ls vault/Approved/
```

## 5. Test MCP Email Server

```bash
# Start server (in one terminal)
uv run python -m backend.mcp_servers.email_server.server

# Send test request (in another terminal)
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | uv run python -m backend.mcp_servers.email_server.server
```

Expected: JSON response with send_email tool

## 6. Test Process Manager

```powershell
# Start all services
.\scripts\start.ps1

# In another terminal, check status
.\scripts\status.ps1

# Stop services
.\scripts\stop.ps1
```

## 7. End-to-End Test

1. Start services: `.\scripts\start.ps1`
2. Send yourself a test email
3. Wait 2 minutes (Gmail watcher interval)
4. Check: `ls vault/Needs_Action/`
5. Wait 30 seconds (Orchestrator interval)
6. Check: `ls vault/Plans/`
7. Check: `ls vault/Pending_Approval/`
8. Approve: `python scripts/approve.py <plan-file>`
9. Check: `ls vault/Done/`

## Troubleshooting

### No action files created
- Check watcher logs: `cat vault/Logs/actions/*.jsonl`
- Verify OAuth tokens exist: `ls config/token.json config/calendar_token.json`

### Plans not generated
- Check orchestrator logs: `cat vault/Logs/decisions/*.jsonl`
- Verify DEV_MODE=true in config/.env

### Approval not working
- Check file exists: `ls vault/Pending_Approval/`
- Verify workflow manager: `cat vault/Logs/workflow/*.jsonl`

## Success Indicators

✅ Calendar watcher detects events
✅ Orchestrator creates plans
✅ Plans routed to Pending_Approval
✅ Approve/reject scripts work
✅ All services start/stop cleanly
✅ Status script shows correct state
