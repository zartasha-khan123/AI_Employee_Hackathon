# Social Media Poster Skill

**Version:** 1.0.0
**Type:** Content Publishing
**Trigger:** Manual or scheduled via Content_Calendar.md
**Requires Approval:** Yes (ALWAYS)

---

## Purpose

Publish approved content to LinkedIn and Twitter with comprehensive safety controls and rate limiting.

---

## Capabilities

- Post text content to LinkedIn (max 3000 chars)
- Post text content to Twitter (max 280 chars)
- Attach images to posts
- Content safety scanning
- Rate limiting (5 posts/day/platform)
- HITL approval workflow
- DEV_MODE simulation

---

## Trigger Conditions

**Automatic:**
- Content_Calendar.md has post marked "Ready" and scheduled within next hour
- LinkedIn watcher detects scheduled post

**Manual:**
- User creates approval file in vault/Approved/ with type: linkedin_post or twitter_post
- User invokes via orchestrator

---

## Input Context

**Required:**
- Post content (text)
- Platform (linkedin or twitter)

**Optional:**
- Image path (for visual posts)
- Scheduled time
- Hashtags (included in content)

**Sources:**
- vault/Content_Calendar.md
- vault/Approved/ (approval files)

---

## Safety Controls

**Content Scanning:**
- Detects sensitive data (SSN, credit cards, passwords)
- Flags prohibited keywords (confidential, internal only)
- Validates character limits
- Redacts sensitive information if found

**Approval Workflow:**
- ALL posts require human approval (no auto-posting)
- Approval file must exist in vault/Approved/
- Approval consumed after successful post

**Rate Limiting:**
- Maximum 5 posts per platform per day
- Tracked in vault/Logs/rate_limits/
- Prevents spam and API abuse

**DEV_MODE:**
- Simulates posts without actually publishing
- Logs to vault/Logs/actions/
- Safe for testing

---

## Workflow

1. **Content Preparation**
   - User adds post to Content_Calendar.md
   - Sets status to "Ready"
   - Schedules time

2. **Detection**
   - LinkedIn watcher detects scheduled post
   - Creates action file in vault/Needs_Action/

3. **Plan Generation**
   - Orchestrator creates plan
   - Moves to vault/Pending_Approval/

4. **Human Review**
   - User reviews post content
   - Approves by moving to vault/Approved/

5. **Execution**
   - Social MCP server posts to platform
   - Consumes approval file
   - Logs action to vault/Logs/actions/
   - Moves approval to vault/Done/

---

## Output Format

**Success:**
```
LinkedIn post published successfully. URL: https://www.linkedin.com/feed/
```

**DEV_MODE:**
```
[DEV_MODE] LinkedIn post simulated. Content length: 150 chars. Image: No
```

**Error:**
```
Rejected: No matching approval file found in vault/Approved/ for LinkedIn post
```

---

## Configuration

**Environment Variables (.env):**
```bash
# LinkedIn session path
LINKEDIN_SESSION_PATH=config/linkedin_session

# Twitter credentials (future)
TWITTER_API_KEY=your-key
TWITTER_API_SECRET=your-secret

# Rate limits (posts per day)
SOCIAL_RATE_LIMIT_LINKEDIN=5
SOCIAL_RATE_LIMIT_TWITTER=5
```

**MCP Configuration (config/mcp.json):**
```json
{
  "mcpServers": {
    "social": {
      "command": "uv",
      "args": ["run", "python", "-m", "backend.mcp_servers.social_server.server"],
      "enabled": true
    }
  }
}
```

---

## Platform-Specific Details

### LinkedIn
- **Character Limit:** 3000
- **Image Support:** Yes (PNG, JPG)
- **Authentication:** Browser session (Playwright)
- **Rate Limit:** 5 posts/day
- **Post Types:** Text, Text+Image, Article Share

### Twitter
- **Character Limit:** 280
- **Image Support:** Yes (PNG, JPG)
- **Authentication:** API keys (not yet implemented)
- **Rate Limit:** 5 posts/day
- **Post Types:** Tweet, Tweet+Image, Thread

---

## Error Handling

**No Approval File:**
- Returns error message
- Logs rejection to vault/Logs/actions/
- Does not post

**Rate Limit Exceeded:**
- Returns error with retry time
- Logs rate limit hit
- Does not post

**Authentication Failed:**
- Returns error message
- Suggests re-authenticating
- Does not post

**Content Too Long:**
- Returns error with character count
- Suggests editing content
- Does not post

---

## Testing

**Unit Tests:**
```bash
uv run pytest tests/test_social_server.py
```

**Manual Test (DEV_MODE):**
```bash
# 1. Ensure DEV_MODE=true in .env
# 2. Create approval file
cat > vault/Approved/test-linkedin-post.md << 'EOF'
---
type: linkedin_post
status: approved
---
Test post from AI Employee! #AI #Automation
EOF

# 3. Test post
uv run python -m backend.mcp_servers.social_server.server

# 4. Check logs
cat vault/Logs/actions/$(date +%Y-%m-%d).json
```

---

## Integration

**Content Calendar:**
- Reads from vault/Content_Calendar.md
- Detects posts marked "Ready"
- Creates action files automatically

**LinkedIn Watcher:**
- Monitors Content_Calendar.md
- Triggers post creation workflow

**Orchestrator:**
- Creates plans for social posts
- Routes to Pending_Approval/
- Executes after approval

---

## Security Considerations

**Session Management:**
- LinkedIn session stored in config/linkedin_session/
- Session files are gitignored
- Re-authentication required if session expires

**Content Safety:**
- All content scanned before posting
- Sensitive data redacted
- Prohibited keywords blocked

**Audit Trail:**
- All posts logged with timestamp
- Approval files preserved in vault/Done/
- Rate limit tracking in vault/Logs/

---

## Future Enhancements

- Twitter API integration (currently placeholder)
- Thread support for long-form content
- Post scheduling (queue posts for future)
- Analytics tracking (likes, comments, shares)
- Automatic hashtag suggestions
- Image optimization and resizing
- Video support
- Multi-platform posting (same content to multiple platforms)
- Post templates for common content types

---

## Limitations

**Current Implementation:**
- LinkedIn posting uses browser automation (may break if UI changes)
- Twitter posting not yet implemented (Platinum tier)
- Post URL extraction is simplified (returns feed URL)
- No analytics or engagement tracking
- No post editing or deletion

**Platform Restrictions:**
- Must comply with LinkedIn Terms of Service
- Must comply with Twitter Terms of Service
- Rate limits enforced by platforms
- Authentication required for each platform

---

## Dependencies

- `playwright` - Browser automation
- `backend.utils.frontmatter` - Approval file parsing
- `backend.utils.logging_utils` - Action logging
- LinkedIn session from linkedin_watcher

---

## Version History

- **1.0.0** (2026-02-22) - Initial implementation
  - LinkedIn posting via browser automation
  - Content safety scanning
  - Rate limiting (5/day)
  - HITL approval workflow
  - DEV_MODE simulation
