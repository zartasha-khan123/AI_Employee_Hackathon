# WhatsApp Watcher Skill

**Type:** Perception Layer
**Status:** Active (Optional)
**Tier:** Silver+

⚠️ **WARNING:** This watcher uses WhatsApp Web automation which may violate WhatsApp's Terms of Service. Use at your own risk. DEV_MODE is enabled by default to prevent actual browser automation.

## Purpose

The WhatsApp Watcher monitors WhatsApp Web for incoming messages and creates action files for important conversations requiring response. It's a perception-only component that never sends messages or marks as read.

## How It Works

1. **Launches headless browser** (Playwright/Chromium)
2. **Navigates to WhatsApp Web** (web.whatsapp.com)
3. **Checks authentication** (QR code scan required first time)
4. **Monitors unread messages** every 60 seconds
5. **Classifies priority** based on keywords
6. **Creates action files** in `vault/Needs_Action/`
7. **Tracks processed messages** to avoid duplicates

## ⚠️ Important Warnings

### Terms of Service
- WhatsApp Web automation may violate WhatsApp ToS
- WhatsApp may ban accounts using automation
- Use at your own risk
- Consider WhatsApp Business API as alternative

### Privacy & Security
- Browser session stored locally
- No message content logged (only metadata)
- Session files should be gitignored
- Never share session files

### Reliability
- WhatsApp Web UI changes frequently
- Automation may break without notice
- Session expires periodically
- Requires manual re-authentication

## Setup

### 1. Install Playwright

```bash
# Add Playwright to dependencies
uv add playwright

# Install browser binaries
uv run playwright install chromium
```

### 2. Run Authentication Setup

```bash
uv run python skills/whatsapp-watcher/scripts/setup_whatsapp_auth.py
```

This will:
- Launch browser (non-headless)
- Navigate to WhatsApp Web
- Display QR code
- Wait for you to scan with phone
- Save session to `config/whatsapp_session/`

### 3. Test the Watcher

```bash
# Single check (dry run)
uv run python backend/watchers/whatsapp_watcher.py --once

# Continuous monitoring (requires DEV_MODE=false)
uv run python backend/watchers/whatsapp_watcher.py
```

## Configuration

### File: `config/whatsapp_config.json`

```json
{
  "poll_interval_seconds": 60,
  "session_path": "config/whatsapp_session",
  "headless": true,

  "priority_keywords": {
    "high": ["urgent", "asap", "emergency", "important", "help"],
    "medium": ["question", "need", "when", "how", "please"]
  },

  "exclude_contacts": ["Spam", "Unknown", "WhatsApp"],
  "exclude_groups": true,
  "max_message_length": 5000,
  "mark_as_read": false,

  "rate_limits": {
    "messages_per_hour": 50,
    "responses_per_day": 20
  }
}
```

### Environment Variables

```bash
WHATSAPP_CHECK_INTERVAL=60
WHATSAPP_SESSION_PATH=config/whatsapp_session
WHATSAPP_HEADLESS=true
```

## Action File Format

Created files: `vault/Needs_Action/whatsapp-{contact-slug}-{timestamp}.md`

### Frontmatter

```yaml
---
type: whatsapp_message
id: WHATSAPP_abc12345_20260215T143022
source: whatsapp_watcher
from: Contact Name
message_preview: "First 200 characters of message..."
received: 2026-02-15T14:30:22Z
priority: high
status: pending
is_group: false
---
```

### Body

- Full message content
- Contact info
- Suggested actions checklist

## Priority Classification

### High Priority
- Contains keywords: urgent, asap, emergency, important, help
- Requires immediate attention

### Medium Priority
- Contains keywords: question, need, when, how, please
- Requires timely response

### Low Priority
- All other messages
- Can be handled later

## Safety Features

### 1. DEV_MODE (Default: ON)
- No browser launch
- Simulates message detection
- Logs to console only
- **ALWAYS keep ON unless you accept ToS risks**

### 2. DRY_RUN (Default: ON)
- Logs actions without creating files
- Safe for testing

### 3. Read-Only Mode
- Never sends messages
- Never marks as read
- Never modifies conversations
- Perception only

### 4. Privacy Protection
- No message content in logs
- Only metadata tracked
- Session encrypted
- No screenshots

### 5. Rate Limiting
- Max 50 messages/hour processed
- Max 20 responses/day
- Prevents aggressive scraping

### 6. Group Exclusion
- Skips group chats by default
- Reduces noise
- Focuses on 1:1 conversations

## Usage

### Start Watcher

```bash
# Continuous monitoring (requires authentication)
uv run python backend/watchers/whatsapp_watcher.py

# Single check (testing)
uv run python backend/watchers/whatsapp_watcher.py --once
```

### Approve Message Response

```bash
# List pending approvals
ls vault/Pending_Approval/

# Approve
python scripts/approve.py whatsapp-john-doe-20260215T143022.md

# Reject
python scripts/reject.py whatsapp-john-doe-20260215T143022.md "Not appropriate"
```

## Workflow

```
WhatsApp Web → Browser Automation → WhatsApp Watcher → vault/Needs_Action/
                                                              ↓
                                                        Orchestrator
                                                              ↓
                                                        vault/Plans/
                                                              ↓
                                                  vault/Pending_Approval/
                                                              ↓
                                                      [HUMAN APPROVAL]
                                                              ↓
                                                      vault/Approved/
                                                              ↓
                                            MCP WhatsApp Server (Future)
                                                              ↓
                                                        vault/Done/
```

## Logging

### Action Logs
`vault/Logs/actions/whatsapp_watcher-{date}.jsonl`

```json
{
  "timestamp": "2026-02-15T14:30:22Z",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "actor": "whatsapp_watcher",
  "action_type": "message_processed",
  "target": "whatsapp-john-doe-20260215T143022.md",
  "result": "success",
  "parameters": {
    "from": "John Doe",
    "priority": "high"
  }
}
```

### Processed Messages
`vault/Logs/processed_messages.json`

Tracks message IDs to prevent duplicates.

## Troubleshooting

### "Playwright not installed"
```bash
uv add playwright
uv run playwright install chromium
```

### "QR code scan required"
```bash
# Run authentication setup
uv run python skills/whatsapp-watcher/scripts/setup_whatsapp_auth.py

# Scan QR code with phone
# Session will be saved automatically
```

### Session expired
- Delete `config/whatsapp_session/`
- Run authentication setup again
- Scan QR code

### No messages detected
- Check browser is running (if headless=false)
- Verify authentication is valid
- Check watcher logs: `vault/Logs/actions/`
- Ensure messages are unread

### Browser crashes
- Check Chromium is installed: `uv run playwright install chromium`
- Try headless=false for debugging
- Check system resources

## Best Practices

### Security
- Keep DEV_MODE=true unless necessary
- Never commit session files
- Use strong device security
- Monitor for suspicious activity

### Privacy
- Only process messages you have permission to read
- Don't share message content
- Respect contact privacy
- Follow data protection laws

### Reliability
- Expect frequent breakage
- Have manual fallback
- Don't rely on automation
- Monitor error logs

### Alternatives
- Consider WhatsApp Business API (official, paid)
- Use email for important communications
- Manual WhatsApp checking
- Third-party integrations (Zapier, etc.)

## Integration with Process Manager

The WhatsApp watcher runs automatically when you start all services (if enabled):

```powershell
.\scripts\start.ps1
```

Check status:

```powershell
.\scripts\status.ps1
```

## Disabling WhatsApp Watcher

If you don't want WhatsApp monitoring:

1. Keep `DEV_MODE=true` (default)
2. Or comment out WhatsApp watcher in `process_manager.py`
3. Or don't run authentication setup

## Future Enhancements

1. **MCP WhatsApp Server** - Send replies via automation
2. **Media Support** - Handle images, videos, voice notes
3. **Group Chat Support** - Monitor specific groups
4. **Contact Filtering** - Whitelist/blacklist contacts
5. **Auto-responses** - Simple acknowledgments
6. **WhatsApp Business API** - Official integration

## Commands

```bash
# Setup authentication
uv run python skills/whatsapp-watcher/scripts/setup_whatsapp_auth.py

# Start watcher
uv run python backend/watchers/whatsapp_watcher.py

# Single check
uv run python backend/watchers/whatsapp_watcher.py --once

# Clear session
rm -rf config/whatsapp_session/

# Check processed messages
cat vault/Logs/processed_messages.json
```

## Files

```
backend/watchers/
└── whatsapp_watcher.py            # Main watcher

config/
├── whatsapp_config.json           # Configuration
└── whatsapp_session/              # Browser session (gitignored)
    └── state.json

vault/Logs/
├── actions/                       # Action logs
└── processed_messages.json        # Duplicate tracking

skills/whatsapp-watcher/
├── SKILL.md                       # This file
└── scripts/
    └── setup_whatsapp_auth.py     # Authentication setup
```

## Legal Disclaimer

This tool is provided for educational purposes only. By using this tool, you acknowledge that:

1. WhatsApp Web automation may violate WhatsApp's Terms of Service
2. Your WhatsApp account may be banned
3. You use this tool at your own risk
4. The developers are not responsible for any consequences
5. You should consult WhatsApp's ToS before use
6. Consider official WhatsApp Business API instead

## References

- [Playwright Documentation](https://playwright.dev/python/)
- [WhatsApp Business API](https://business.whatsapp.com/products/business-platform)
- Base Watcher: `backend/watchers/base_watcher.py`
- Gmail Watcher: `backend/watchers/gmail_watcher.py` (similar pattern)
