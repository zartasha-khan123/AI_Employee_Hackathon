# Approval Workflow Skill

**Type:** Human-in-the-Loop (HITL)
**Status:** Active
**Tier:** Silver

## Purpose

The Approval Workflow provides human oversight for sensitive AI Employee actions. It ensures that critical decisions require explicit human approval before execution, maintaining safety and control.

## How It Works

1. **Orchestrator creates plan** from action file
2. **Approval logic determines** if human review needed
3. **Plan moved to Pending_Approval** folder
4. **Human reviews plan** in Obsidian or via CLI
5. **Human approves or rejects** using scripts
6. **Orchestrator executes** approved plans
7. **Results logged** to Done or Rejected folders

## Approval Requirements

Plans require human approval if:

### Always Require Approval
- High priority actions (urgent, critical)
- Email to multiple recipients (>5 CC)
- Financial transactions (payments, invoices)
- Contract or legal documents
- Unknown action types

### Can Auto-Approve
- Low priority routine actions
- Standard acknowledgment emails (single recipient)
- Calendar event acceptance (internal meetings)
- Read-only operations

## Approval Scripts

### Approve a Plan

```bash
python scripts/approve.py <plan-filename>
```

**Example:**
```bash
python scripts/approve.py plan-email-client-demo-20260215T143022.md
```

**What it does:**
1. Validates plan exists in Pending_Approval
2. Updates frontmatter: `status: approved`, `approved_by: human`, `approved_at: timestamp`
3. Moves file to Approved folder
4. Logs approval to audit trail
5. Orchestrator executes on next cycle

### Reject a Plan

```bash
python scripts/reject.py <plan-filename> "<reason>"
```

**Example:**
```bash
python scripts/reject.py plan-email-client-demo-20260215T143022.md "Timing not appropriate"
```

**What it does:**
1. Validates plan exists in Pending_Approval
2. Updates frontmatter: `status: rejected`, `rejected_by: human`, `rejection_reason: reason`
3. Moves file to Rejected folder
4. Logs rejection to audit trail
5. Plan will not be executed

## Workflow States

```
Action File → Plan → Pending_Approval → [HUMAN DECISION]
                                              ↓
                                    Approved ← → Rejected
                                       ↓              ↓
                                     Done         Rejected/
```

### Status Transitions

1. **pending** - Action detected by watcher
2. **planning** - Orchestrator generating plan
3. **pending_approval** - Awaiting human review
4. **approved** - Human approved, ready for execution
5. **rejected** - Human rejected, will not execute
6. **executing** - Currently being executed
7. **completed** - Successfully executed
8. **failed** - Execution failed

## Review Process

### 1. Check Pending Approvals

```bash
# PowerShell
.\scripts\status.ps1

# Or manually
ls vault/Pending_Approval/
```

### 2. Review Plan Details

Open plan file in Obsidian or text editor:

```yaml
---
type: plan
id: PLAN_abc12345_20260215
action_type: email
priority: high
requires_approval: true
sensitivity: medium
---

## Action Summary
Send acknowledgment email to client

## Proposed Action
Draft and send professional acknowledgment...

## Risk Assessment
- Sensitivity: Medium (external communication)
- Reversibility: Low (email cannot be unsent)
- Impact: Medium (client relationship)

## Approval Required
Yes - high priority external communication
```

### 3. Make Decision

**Approve if:**
- Action aligns with business goals
- Risk level is acceptable
- Timing is appropriate
- Content is accurate and professional

**Reject if:**
- Action is inappropriate or risky
- Timing is wrong
- Content needs revision
- Better handled manually

### 4. Execute Decision

```bash
# Approve
python scripts/approve.py plan-email-client-demo-20260215T143022.md

# Reject
python scripts/reject.py plan-email-client-demo-20260215T143022.md "Needs revision"
```

## Dashboard Integration

The vault Dashboard shows pending approvals:

```markdown
# AI Employee Dashboard

## Pending Approvals: 3

- [[plan-email-client-demo-20260215T143022.md]] - High Priority
- [[plan-calendar-board-meeting-20260215T150000.md]] - Medium Priority
- [[plan-email-invoice-reminder-20260215T160000.md]] - Low Priority

## Quick Actions

- [Approve All Low Priority](obsidian://approve-low-priority)
- [View Approval Queue](vault/Pending_Approval/)
```

## Audit Logging

All approval decisions logged to `vault/Logs/audit/`:

```json
{
  "timestamp": "2026-02-15T14:30:22Z",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "actor": "human",
  "action_type": "plan_approved",
  "target": "plan-email-client-demo-20260215T143022.md",
  "result": "success"
}
```

## Safety Features

### 1. Explicit Approval Required
- No automatic approval for sensitive actions
- Human must explicitly run approve script
- Cannot approve by accident

### 2. Rejection Reason Required
- Must provide reason for rejection
- Helps improve future plans
- Creates audit trail

### 3. Audit Trail
- All decisions logged with timestamp
- Correlation IDs link related events
- Full history preserved

### 4. Rollback Plans
- Every plan includes rollback strategy
- Documents how to undo if needed
- Reduces risk of irreversible actions

## Notification Options

### Email Notifications (Future)
```bash
# Configure email notifications for pending approvals
APPROVAL_NOTIFICATION_EMAIL=you@example.com
APPROVAL_NOTIFICATION_THRESHOLD=high  # Only notify for high priority
```

### Slack Notifications (Future)
```bash
# Configure Slack notifications
APPROVAL_SLACK_WEBHOOK=https://hooks.slack.com/...
APPROVAL_SLACK_CHANNEL=#ai-employee-approvals
```

## Batch Operations

### Approve Multiple Plans

```bash
# Approve all low priority plans
for file in vault/Pending_Approval/plan-*-low-*.md; do
    python scripts/approve.py "$(basename "$file")"
done
```

### Review by Priority

```bash
# List high priority plans
grep -l "priority: high" vault/Pending_Approval/*.md
```

## Troubleshooting

### "Plan not found in Pending_Approval"
- Check filename spelling
- Verify plan hasn't already been approved/rejected
- Run `.\scripts\status.ps1` to see available plans

### Approval not executing
- Check orchestrator is running: `.\scripts\status.ps1`
- Verify plan moved to Approved folder
- Check orchestrator logs: `vault/Logs/executions/`

### Can't find approval scripts
- Ensure you're in project root directory
- Scripts located in `scripts/` folder
- Run with: `python scripts/approve.py <filename>`

## Best Practices

### 1. Review Promptly
- Check pending approvals daily
- High priority items within 1 hour
- Set up notifications for urgent items

### 2. Provide Clear Rejection Reasons
- Explain why rejected
- Suggest improvements
- Help AI learn from feedback

### 3. Verify Before Approving
- Read full plan content
- Check risk assessment
- Verify timing is appropriate
- Confirm action aligns with goals

### 4. Monitor Execution
- Check Done folder after approval
- Review execution logs
- Verify expected outcome

### 5. Adjust Approval Logic
- If too many false positives, adjust `plan_generator.py`
- If missing risky actions, tighten approval requirements
- Balance safety with efficiency

## Commands

```bash
# Check status and pending approvals
.\scripts\status.ps1

# List pending approvals
ls vault/Pending_Approval/

# Approve a plan
python scripts/approve.py plan-email-test-20260215.md

# Reject a plan
python scripts/reject.py plan-email-test-20260215.md "Not appropriate"

# View approved plans
ls vault/Approved/

# View rejected plans
ls vault/Rejected/

# View completed actions
ls vault/Done/

# View audit logs
cat vault/Logs/audit/workflow_manager-*.jsonl
```

## Files

```
scripts/
├── approve.py                     # Approval script
├── reject.py                      # Rejection script
├── status.ps1                     # Status checker
├── start.ps1                      # Start services
└── stop.ps1                       # Stop services

vault/
├── Pending_Approval/              # Plans awaiting review
├── Approved/                      # Approved plans (executing)
├── Rejected/                      # Rejected plans
├── Done/                          # Completed actions
└── Logs/
    └── audit/                     # Approval/rejection logs

backend/orchestrator/
└── workflow_manager.py            # Approval logic
```

## Next Steps

After Approval Workflow is operational:
1. Test end-to-end: Action → Plan → Approval → Execution
2. Adjust approval thresholds based on experience
3. Add notification integrations (email, Slack)
4. Implement batch approval UI
5. Create approval analytics dashboard

## References

- Workflow Manager: `backend/orchestrator/workflow_manager.py`
- Approval Script: `scripts/approve.py`
- Rejection Script: `scripts/reject.py`
- Orchestrator: `backend/orchestrator/main.py`
