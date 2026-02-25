# Email Sender Skill

**Type:** Action Layer (MCP Server)
**Status:** Active
**Tier:** Silver

## Purpose

The Email Sender MCP server provides email sending capabilities with built-in safety controls. It's the first action capability of the AI Employee, allowing the orchestrator to send emails after human approval.

## How It Works

1. **MCP Protocol:** stdio-based server following Model Context Protocol
2. **Safety Checks:** Validates recipients, scans for sensitive data, enforces rate limits
3. **DEV_MODE:** Simulates sends without actual SMTP (default: ON)
4. **SMTP Integration:** Connects to Gmail (or other SMTP) to send real emails
5. **Audit Logging:** All sends logged to vault

## Safety Features

### 1. DEV_MODE (Default: ON)
- Simulates email sending without actual SMTP
- Logs all details to console
- Safe for testing and development
- Set `DEV_MODE=false` in `.env` for production

### 2. Recipient Allowlist
- Only approved recipients can receive emails
- Configure in `ALLOWED_RECIPIENTS` env variable
- Supports domain wildcards: `*@example.com`
- Blocks all others in production mode

### 3. Content Scanning
Blocks emails containing:
- Passwords (`password: xyz123`)
- Credit card numbers (16 digits)
- Social Security Numbers (XXX-XX-XXXX)
- API keys (`api_key: abc123`)

### 4. Rate Limiting
- 10 emails per hour (configurable)
- 50 emails per day (configurable)
- Prevents runaway automation
- Configured in `config/rate_limits.json`

### 5. Bulk Send Protection
- Blocks emails with >5 CC recipients
- Requires explicit approval for bulk sends
- Prevents accidental mass emails

## Configuration

### Environment Variables

Add to `config/.env`:

```bash
# Email MCP Server
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALLOWED_RECIPIENTS=user1@example.com,user2@example.com,*@yourcompany.com

# Safety
DEV_MODE=true
```

### Gmail App Password Setup

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Generate password for "Mail" on "Other (Custom name)"
5. Copy 16-character password to `SMTP_PASSWORD` in `.env`

**Important:** Use App Password, NOT your regular Gmail password!

### MCP Configuration

Already configured in `config/mcp.json`:

```json
{
  "mcpServers": {
    "email": {
      "command": "uv",
      "args": ["run", "python", "-m", "backend.mcp_servers.email_server.server"],
      "env": {
        "DEV_MODE": "${DEV_MODE:-true}",
        "SMTP_HOST": "${SMTP_HOST:-smtp.gmail.com}",
        "SMTP_PORT": "${SMTP_PORT:-587}",
        "SMTP_USER": "${SMTP_USER}",
        "SMTP_PASSWORD": "${SMTP_PASSWORD}",
        "ALLOWED_RECIPIENTS": "${ALLOWED_RECIPIENTS}"
      },
      "enabled": true
    }
  }
}
```

## MCP Tools

### send_email

Send an email with safety controls.

**Parameters:**
- `to` (string, required): Recipient email address
- `subject` (string, required): Email subject line
- `body` (string, required): Email body (plain text or HTML)
- `cc` (array, optional): CC recipients

**Returns:**
```json
{
  "status": "success",
  "message_id": "<abc123@smtp.gmail.com>",
  "message": "Email sent to user@example.com",
  "dev_mode": true
}
```

**Blocked Response:**
```json
{
  "status": "blocked",
  "reason": "Recipient not in allowlist",
  "details": "user@example.com is not in ALLOWED_RECIPIENTS"
}
```

## Testing

### 1. Test MCP Server (stdio)

```bash
# Start server
uv run python -m backend.mcp_servers.email_server.server

# Send test request (paste JSON and press Enter)
{"jsonrpc":"2.0","id":1,"method":"tools/list"}

# Expected response: list of tools including send_email
```

### 2. Test Email Send (DEV_MODE)

```bash
# Create test script
cat > test_email.py << 'EOF'
import json
import subprocess

request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "send_email",
        "arguments": {
            "to": "test@example.com",
            "subject": "Test Email",
            "body": "This is a test email from AI Employee."
        }
    }
}

proc = subprocess.Popen(
    ["uv", "run", "python", "-m", "backend.mcp_servers.email_server.server"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)

stdout, _ = proc.communicate(json.dumps(request) + "\n")
print(stdout)
EOF

python test_email.py
```

### 3. Test Real Send (Production)

```bash
# Set DEV_MODE=false in .env
# Add your email to ALLOWED_RECIPIENTS
# Configure SMTP credentials

# Send test email to yourself
python test_email.py
```

## Integration with Orchestrator

1. Orchestrator creates plan for email action
2. Plan moved to Pending_Approval (if required)
3. Human approves via `scripts/approve.py`
4. Orchestrator executes plan by calling MCP email server
5. Email sent (or simulated in DEV_MODE)
6. Result logged to vault/Done/

## Troubleshooting

### "Authentication failed"
- Check `SMTP_USER` is correct email address
- Verify `SMTP_PASSWORD` is Gmail App Password (not account password)
- Ensure 2-Step Verification is enabled on Google Account

### "Recipient not in allowlist"
- Add recipient to `ALLOWED_RECIPIENTS` in `.env`
- Use `*@domain.com` to allow entire domain
- Or set `DEV_MODE=true` to bypass allowlist

### "Rate limit exceeded"
- Wait for rate limit window to reset (1 hour or 24 hours)
- Adjust limits in `config/rate_limits.json`
- Check `vault/Logs/` for send history

### "Sensitive data detected"
- Remove passwords, credit cards, SSNs from email body
- Use placeholders or links instead of sensitive data
- Review safety.py patterns if false positive

## Files

```
backend/mcp_servers/email_server/
├── __init__.py                    # Package init
├── server.py                      # MCP protocol handler
├── email_sender.py                # SMTP integration
└── safety.py                      # Safety controls

skills/email-sender/
└── SKILL.md                       # This file

config/
├── mcp.json                       # MCP server configuration
├── .env                           # SMTP credentials
└── rate_limits.json               # Rate limit configuration

vault/Logs/
└── executions/                    # Email send logs
```

## Next Steps

After Email MCP Server is operational:
1. Test end-to-end: Email watcher → Orchestrator → Approval → Email send
2. Implement additional MCP servers (Calendar, Payments, Social)
3. Add more sophisticated approval logic
4. Integrate with process management for 24/7 operation

## References

- [Model Context Protocol](https://modelcontextprotocol.io)
- [Gmail SMTP Settings](https://support.google.com/mail/answer/7126229)
- MCP Server: `backend/mcp_servers/email_server/server.py`
- Safety Controls: `backend/mcp_servers/email_server/safety.py`
