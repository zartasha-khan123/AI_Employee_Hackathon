# Calendar Watcher Skill

**Type:** Perception Layer
**Status:** Active
**Tier:** Silver

## Purpose

The Calendar Watcher monitors Google Calendar for upcoming events that require preparation and creates action files in the vault. It's a perception-only component that never modifies calendar events.

## How It Works

1. **Polls Google Calendar** every 5 minutes (configurable)
2. **Looks ahead** 48 hours for upcoming events
3. **Filters events** that require preparation:
   - Events with external attendees
   - Events with preparation keywords (prepare, review, present, demo)
   - Events within 2 hours (urgent preparation needed)
4. **Creates action files** in `vault/Needs_Action/` with event details
5. **Tracks processed events** to avoid duplicates

## Configuration

### File: `config/calendar_config.json`

```json
{
  "poll_interval_seconds": 300,
  "lookahead_hours": 48,
  "preparation_threshold_hours": 2,
  "priority_keywords": {
    "high": ["urgent", "board", "executive", "client", "demo"],
    "medium": ["review", "sync", "planning", "1:1"]
  },
  "exclude_event_types": ["focus time", "lunch", "break"],
  "vip_domains": ["client.com", "partner.com"]
}
```

### Environment Variables

```bash
CALENDAR_CREDENTIALS_PATH=config/credentials.json
CALENDAR_TOKEN_PATH=config/calendar_token.json
CALENDAR_CHECK_INTERVAL=300
```

## Setup

### 1. Enable Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/library)
2. Search for "Google Calendar API"
3. Click "Enable"

### 2. Run OAuth Setup

```bash
uv run python skills/calendar-watcher/scripts/setup_calendar_oauth.py
```

This will:
- Use existing `config/credentials.json` (same as Gmail)
- Open browser for authorization
- Save token to `config/calendar_token.json`

### 3. Test the Watcher

```bash
# Single check (dry run)
uv run python backend/watchers/calendar_watcher.py --once

# Continuous monitoring
uv run python backend/watchers/calendar_watcher.py
```

## Action File Format

Created files: `vault/Needs_Action/calendar-{event-slug}-{timestamp}.md`

### Frontmatter

```yaml
---
type: calendar_event
id: EVENT_abc12345_20260215T143022
source: calendar_watcher
event_id: google_calendar_event_id
summary: "Client Demo - Q1 Product Review"
start_time: "2026-02-16T14:00:00Z"
end_time: "2026-02-16T15:00:00Z"
attendees:
  - client@example.com
  - team@company.com
priority: high
status: pending
requires_preparation: true
---
```

### Body

- Event details (time, location, attendees)
- Description
- Preparation checklist
- Link to view in Calendar

## Priority Classification

### High Priority
- Contains keywords: urgent, board, executive, client, demo, critical
- Has VIP domain attendees (configured in `vip_domains`)
- Starts within 2 hours

### Medium Priority
- Contains keywords: review, sync, planning, 1:1
- Has external attendees

### Low Priority
- All other events requiring preparation

## Exclusions

Events are skipped if:
- Already processed (tracked in `vault/Logs/processed_events.json`)
- Match exclusion patterns (focus time, lunch, break, personal)
- No preparation required (internal 1:1s, no special keywords)

## Safety Features

### DEV_MODE (Default: ON)
- Set `DEV_MODE=true` in `.env`
- Logs all actions without creating files
- Safe for testing

### DRY_RUN (Default: ON)
- Set `DRY_RUN=true` in `.env`
- Simulates action file creation
- Logs to `vault/Logs/actions/`

### Read-Only
- **Never modifies calendar events**
- **Never deletes events**
- **Never accepts/declines invitations**
- Only reads and creates vault files

## Logging

### Action Logs
`vault/Logs/actions/calendar_watcher-{date}.jsonl`

```json
{
  "timestamp": "2026-02-15T14:30:22Z",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "actor": "calendar_watcher",
  "action_type": "event_processed",
  "target": "calendar-client-demo-20260215T143022.md",
  "result": "success",
  "parameters": {
    "event_id": "abc123",
    "summary": "Client Demo",
    "priority": "high"
  }
}
```

### Error Logs
`vault/Logs/errors/calendar_watcher-{date}.jsonl`

## Integration with Orchestrator

1. Calendar Watcher creates action file in `Needs_Action/`
2. Orchestrator detects new file
3. Orchestrator invokes Claude Code to create preparation plan
4. Plan moved to `Pending_Approval/` for human review
5. After approval, actions executed via MCP servers

## Troubleshooting

### "No valid Calendar token"
Run: `uv run python skills/calendar-watcher/scripts/setup_calendar_oauth.py`

### "Permission denied" (403)
- Ensure Calendar API is enabled in Google Cloud Console
- Check OAuth scopes include `calendar.readonly`

### "Rate limited" (429)
- Watcher implements exponential backoff
- Default poll interval: 5 minutes (well within limits)

### No events detected
- Check `lookahead_hours` in config (default: 48)
- Verify events have external attendees or preparation keywords
- Check exclusion patterns in config

## Commands

```bash
# Setup OAuth
uv run python skills/calendar-watcher/scripts/setup_calendar_oauth.py

# Single check (dry run)
uv run python backend/watchers/calendar_watcher.py --once

# Continuous monitoring
uv run python backend/watchers/calendar_watcher.py

# Auth only (refresh token)
uv run python backend/watchers/calendar_watcher.py --auth-only
```

## Files

```
skills/calendar-watcher/
├── SKILL.md                              # This file
└── scripts/
    └── setup_calendar_oauth.py           # OAuth setup

backend/watchers/
└── calendar_watcher.py                   # Main watcher

config/
├── calendar_config.json                  # Configuration
├── credentials.json                      # OAuth client (shared with Gmail)
└── calendar_token.json                   # OAuth token

vault/Logs/
├── processed_events.json                 # Deduplication tracking
├── actions/calendar_watcher-*.jsonl      # Action logs
└── errors/calendar_watcher-*.jsonl       # Error logs
```

## Next Steps

After Calendar Watcher is operational:
1. Implement Orchestrator (Phase 2) to process action files
2. Add MCP Email Server (Phase 3) for sending responses
3. Implement HITL approval workflow (Phase 4)
4. Set up process management (Phase 5)

## References

- [Google Calendar API Documentation](https://developers.google.com/calendar/api/v3/reference)
- Base Watcher: `backend/watchers/base_watcher.py`
- Gmail Watcher: `backend/watchers/gmail_watcher.py` (similar pattern)
