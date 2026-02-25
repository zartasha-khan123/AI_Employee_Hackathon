# CEO Briefing Generator Skill

**Version:** 1.0.0
**Type:** Automated Reporting
**Trigger:** Daily at 6:00 AM or on-demand
**Requires Approval:** No

---

## Purpose

Generate a daily executive briefing that summarizes key vault activity, pending items, and metrics for CEO review.

---

## Capabilities

- Aggregate last 24 hours of vault activity
- Identify urgent items requiring attention
- List pending approvals
- Summarize completed actions
- Display upcoming calendar events (next 3 days)
- Calculate activity metrics

---

## Trigger Conditions

**Automatic:**
- Daily at 6:00 AM (configurable via BRIEFING_TIME in .env)

**Manual:**
- User runs: `uv run python backend/briefing/generator.py`
- User invokes via orchestrator

---

## Input Context

Reads from vault directories:
- `vault/Needs_Action/` - Urgent items
- `vault/Pending_Approval/` - Items awaiting approval
- `vault/Done/` - Completed actions (last 24h)
- `vault/Logs/` - Activity metrics

---

## Output Format

Creates markdown file in `vault/Briefings/YYYY-MM-DD-briefing.md` with sections:

1. **Executive Summary** - 3-5 bullet points of key highlights
2. **Urgent Items** - High-priority items requiring attention
3. **Pending Approvals** - Items awaiting human review
4. **Completed Actions** - Actions completed in last 24 hours
5. **Upcoming Events** - Calendar events for next 3 days
6. **Activity Metrics** - Quantitative summary

---

## Example Output

```markdown
---
type: ceo_briefing
date: 2026-02-22
generated_at: 2026-02-22T06:00:00Z
---

# CEO Daily Briefing - February 22, 2026

## Executive Summary

- 5 action(s) completed in last 24 hours
- 2 item(s) awaiting your approval
- 1 urgent item(s) require attention

---

## 🚨 Urgent Items

### email-invoice-request-acme-corp
- **Type:** email
- **Priority:** high
- **Created:** 2026-02-21T18:30:00Z

---

## ⏳ Pending Approvals

- **plan-send-invoice-acme** (invoice_send) - Priority: medium
- **plan-linkedin-post-announcement** (linkedin_post) - Priority: low

---

## ✅ Completed Actions (Last 24h)

- ✅ **email-reply-client-meeting** (email_reply)
- ✅ **calendar-accept-team-sync** (calendar_event)
- ✅ **linkedin-post-product-launch** (linkedin_post)

---

## 📅 Upcoming Events (Next 3 Days)

- Board Meeting - 2026-02-23 10:00 AM
- Client Demo - 2026-02-24 2:00 PM

---

## 📊 Activity Metrics

- Actions Completed: 5
- Pending Approvals: 2
- Urgent Items: 1

*Generated at 2026-02-22T06:00:00Z*
```

---

## Configuration

**Environment Variables (.env):**
```bash
# Briefing generation time (24-hour format)
BRIEFING_TIME=06:00

# Vault path
VAULT_PATH=./vault
```

---

## Safety & Permissions

- **DEV_MODE:** Not applicable (read-only operation)
- **Approval Required:** No (informational only)
- **Rate Limiting:** Once per day (automatic), unlimited manual
- **Data Access:** Read-only access to vault

---

## Error Handling

**Missing Vault Directories:**
- Returns empty sections if directories don't exist
- Logs warning but continues generation

**Parse Errors:**
- Skips malformed files
- Logs warning with file path
- Continues with remaining files

**File Write Errors:**
- Logs error
- Returns briefing content even if save fails

---

## Testing

**Unit Tests:**
```bash
uv run pytest tests/test_briefing_generator.py
```

**Manual Test:**
```bash
# Generate briefing now
uv run python backend/briefing/generator.py

# Check output
cat vault/Briefings/$(date +%Y-%m-%d)-briefing.md
```

---

## Integration

**Process Manager:**
- Added to `backend/orchestrator/process_manager.py`
- Scheduled task runs daily at configured time
- Logs generation to `vault/Logs/actions/`

**Orchestrator:**
- Can be invoked via plan: `type: generate_briefing`
- No approval required

---

## Future Enhancements

- Email briefing to user
- Slack/Discord notification
- Weekly/monthly summary reports
- Trend analysis (week-over-week metrics)
- AI-generated insights and recommendations
- Integration with calendar for event details
- Financial summary from Accounting folder

---

## Dependencies

- `backend.utils.frontmatter` - Parse markdown frontmatter
- `backend.utils.timestamps` - ISO timestamp generation
- `backend.utils.logging_utils` - Structured logging

---

## Version History

- **1.0.0** (2026-02-22) - Initial implementation
  - Daily briefing generation
  - 6 sections: summary, urgent, pending, completed, events, metrics
  - Automatic scheduling support
