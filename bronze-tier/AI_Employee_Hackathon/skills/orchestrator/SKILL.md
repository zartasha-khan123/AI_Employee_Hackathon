# Orchestrator Skill

**Type:** Reasoning Layer
**Status:** Active
**Tier:** Silver

## Purpose

The Orchestrator is the reasoning layer of the AI Employee. It monitors the vault for new action files, invokes Claude Code to generate execution plans, and manages the workflow through approval and execution.

## Architecture

```
Action Files → Orchestrator → Plans → Approval → Execution → Done
(Needs_Action)                (Plans)  (Pending/Approved)      (Done)
```

## How It Works

1. **File Monitor** watches `vault/Needs_Action/` for new files
2. **Plan Generator** invokes Claude Code to create execution plans
3. **Workflow Manager** routes plans based on approval requirements
4. **Execution Engine** executes approved plans via MCP servers
5. **Audit Logger** tracks all decisions and actions

## Components

### File Monitor
- Uses `watchdog` library to detect new files
- Triggers plan generation when action files appear
- Debounces rapid changes to avoid duplicate processing

### Plan Generator
- Reads action file and extracts context
- Loads Company_Handbook.md and Business_Goals.md
- Invokes Claude Code with orchestrator skill
- Parses generated plan and extracts frontmatter

### Workflow Manager
- Moves files between vault folders
- Updates frontmatter status fields
- Logs all transitions to audit trail
- Manages approval workflow

### Approval Logic
Plans require human approval if:
- High priority (urgent, critical)
- Sensitive action (email to multiple recipients, payments)
- Unknown action type
- Contains keywords: contract, legal, financial

Plans can be auto-approved if:
- Low priority routine actions
- Standard acknowledgment emails
- Calendar event acceptance (internal meetings)

## Configuration

### Environment Variables

```bash
VAULT_PATH=./vault
ORCHESTRATOR_CHECK_INTERVAL=30
DEV_MODE=true
DRY_RUN=true
```

### DEV_MODE (Default: ON)
- Simulates plan generation without calling Claude Code
- Uses mock plans based on action type
- Safe for testing orchestrator workflow

### DRY_RUN (Default: ON)
- Logs execution without actually running MCP servers
- Moves files through workflow normally
- Useful for testing approval workflow

## Usage

### Start Orchestrator

```bash
# Continuous monitoring
uv run python backend/orchestrator/main.py

# Single cycle (for testing)
uv run python backend/orchestrator/main.py --once
```

### Manual Testing

1. Create test action file in `vault/Needs_Action/`:

```yaml
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
```

2. Watch orchestrator logs:
```bash
tail -f vault/Logs/decisions/*.jsonl
```

3. Check plan created in `vault/Plans/`

4. If requires approval, check `vault/Pending_Approval/`

## Plan Format

Generated plans: `vault/Plans/plan-{action-slug}-{timestamp}.md`

### Frontmatter

```yaml
---
type: plan
id: PLAN_abc12345_20260215
source: orchestrator
action_id: EMAIL_xyz789_20260215
action_type: email
priority: medium
status: pending
requires_approval: true
created_at: 2026-02-15T14:30:22Z
sensitivity: medium
---
```

### Body

- Action Summary
- Proposed Action
- Steps (numbered checklist)
- Risk Assessment (sensitivity, reversibility, impact)
- Approval Required (yes/no with reason)
- Rollback Plan

## Workflow States

### Action File Lifecycle

```
Needs_Action → Plans → Pending_Approval → Approved → Done
                    ↘                   ↗
                      (auto-approved)
                    ↘
                      Rejected
```

### Status Transitions

1. **pending** - Action file created by watcher
2. **planning** - Orchestrator generating plan
3. **pending_approval** - Plan awaiting human review
4. **approved** - Plan approved (human or auto)
5. **rejected** - Plan rejected by human
6. **executing** - Plan being executed via MCP
7. **completed** - Execution finished successfully
8. **failed** - Execution failed

## Logging

### Decision Logs
`vault/Logs/decisions/orchestrator-{date}.jsonl`

```json
{
  "timestamp": "2026-02-15T14:30:22Z",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "actor": "orchestrator",
  "action_type": "plan_created",
  "source": "email-test-20260215T143022.md",
  "target": "plan-email-test-20260215T143022.md",
  "requires_approval": true,
  "result": "success"
}
```

### Execution Logs
`vault/Logs/executions/orchestrator-{date}.jsonl`

### Error Logs
`vault/Logs/errors/orchestrator-{date}.jsonl`

## Integration with Watchers

1. Gmail Watcher creates action file in `Needs_Action/`
2. Calendar Watcher creates action file in `Needs_Action/`
3. Orchestrator detects new file via File Monitor
4. Plan Generator creates plan
5. Workflow Manager routes to Pending_Approval or Approved
6. Human approves via `scripts/approve.py` (if needed)
7. Orchestrator executes via MCP servers
8. Result logged to `Done/`

## Integration with MCP Servers

When executing approved plans, orchestrator:
1. Parses plan frontmatter to determine action type
2. Invokes appropriate MCP server (email, calendar, etc.)
3. Passes parameters from plan
4. Captures execution result
5. Updates plan status and moves to Done
6. Logs execution to audit trail

## Troubleshooting

### Orchestrator not detecting files
- Check file monitor is running: `ps aux | grep orchestrator`
- Verify `vault/Needs_Action/` exists
- Check file permissions

### Plans not being generated
- Check DEV_MODE setting (should be true for testing)
- Verify action file has valid frontmatter
- Check orchestrator logs for errors

### Plans stuck in Pending_Approval
- Use `scripts/approve.py` to approve manually
- Check approval logic in plan_generator.py
- Verify workflow_manager is running

### Execution not happening
- Check DRY_RUN setting (should be false for real execution)
- Verify MCP servers are configured
- Check execution logs for errors

## Commands

```bash
# Start orchestrator
uv run python backend/orchestrator/main.py

# Single cycle (testing)
uv run python backend/orchestrator/main.py --once

# Approve a plan
uv run python scripts/approve.py plan-email-test-20260215.md

# Reject a plan
uv run python scripts/reject.py plan-email-test-20260215.md "Not appropriate"

# View pending approvals
ls vault/Pending_Approval/

# View approved plans
ls vault/Approved/

# View completed actions
ls vault/Done/
```

## Files

```
backend/orchestrator/
├── __init__.py                    # Package init
├── main.py                        # Main orchestration loop
├── file_monitor.py                # Watchdog-based file monitoring
├── plan_generator.py              # Claude Code integration
└── workflow_manager.py            # File workflow management

skills/orchestrator/
└── SKILL.md                       # This file

vault/
├── Needs_Action/                  # Action files from watchers
├── Plans/                         # Generated plans
├── Pending_Approval/              # Plans awaiting approval
├── Approved/                      # Approved plans ready for execution
├── Rejected/                      # Rejected plans
├── Done/                          # Completed actions
└── Logs/
    ├── decisions/                 # Orchestrator decisions
    ├── executions/                # Execution results
    └── errors/                    # Error logs
```

## Next Steps

After Orchestrator is operational:
1. Implement MCP Email Server (Phase 3) for sending emails
2. Create approval scripts (Phase 4) for HITL workflow
3. Set up process management (Phase 5) to run all services
4. Test end-to-end workflow: Email → Plan → Approval → Execution

## References

- File Monitor: `backend/orchestrator/file_monitor.py`
- Plan Generator: `backend/orchestrator/plan_generator.py`
- Workflow Manager: `backend/orchestrator/workflow_manager.py`
- Watchers: `backend/watchers/`
