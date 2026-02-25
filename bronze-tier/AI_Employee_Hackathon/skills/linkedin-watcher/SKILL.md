# LinkedIn Watcher Skill

**Type:** Perception Layer
**Status:** Active
**Tier:** Silver+

## Purpose

The LinkedIn Watcher monitors local content sources (Content Calendar, Business Updates, Announcements) and creates action files for LinkedIn posting. It's a perception-only component that never posts to LinkedIn directly.

## How It Works

1. **Polls content sources** every 10 minutes (configurable)
2. **Scans for ready posts:**
   - Content_Calendar.md (scheduled posts)
   - Business_Updates/ folder (draft posts)
   - Announcements/ folder (company announcements)
3. **Validates content** (length, keywords, duplicates)
4. **Creates action files** in `vault/Needs_Action/`
5. **Tracks posted content** to avoid duplicates

## Content Sources

### 1. Content Calendar (`vault/Content_Calendar.md`)

Schedule posts with specific dates and times.

**Format:**
```markdown
### 2026-02-16 10:00 AM
**Type:** Business Update
**Status:** Ready

Your post content here...

**Hashtags:** #YourHashtag
**Media:** path/to/image.png
```

**Status Values:**
- `Draft` - Not ready, watcher ignores
- `Ready` - Ready to post, watcher detects
- `Posted` - Already posted, move to archive

### 2. Business Updates (`vault/Business_Updates/`)

Drop markdown files here for ad-hoc posts.

**Example:** `vault/Business_Updates/q1-results.md`
```markdown
---
hashtags: ["#BusinessGrowth", "#Q1Results"]
media: images/chart.png
---

Excited to share our Q1 results! Revenue up 25%...
```

### 3. Announcements (`vault/Announcements/`)

Company announcements (high priority).

**Example:** `vault/Announcements/new-partnership.md`
```markdown
---
hashtags: ["#Partnership", "#BigNews"]
---

🎉 Thrilled to announce our partnership with...
```

## Configuration

### File: `config/linkedin_config.json`

```json
{
  "poll_interval_seconds": 600,
  "content_sources": [
    "vault/Content_Calendar.md",
    "vault/Business_Updates/",
    "vault/Announcements/"
  ],
  "rate_limits": {
    "posts_per_day": 3,
    "posts_per_week": 10
  },
  "exclude_keywords": [
    "draft",
    "wip",
    "do not post",
    "internal only",
    "confidential"
  ]
}
```

### Environment Variables

```bash
LINKEDIN_CHECK_INTERVAL=600  # 10 minutes
```

## Action File Format

Created files: `vault/Needs_Action/linkedin-{slug}-{timestamp}.md`

### Frontmatter

```yaml
---
type: linkedin_post
id: LINKEDIN_abc12345_20260215T143022
source: linkedin_watcher
content_source: Content_Calendar.md
post_type: business_update
scheduled_date: 2026-02-16T10:00:00Z
priority: medium
status: pending
requires_approval: true
---
```

### Body

- Post content (max 3000 characters)
- Metadata (type, hashtags, media)
- Suggested actions checklist

## Post Types

### Business Update (Medium Priority)
- Company news and updates
- Achievements and milestones
- Team highlights
- Requires approval

### Announcement (High Priority)
- Major company announcements
- Partnerships and collaborations
- Product launches
- Always requires approval

### Article Share (Low Priority)
- Industry articles and insights
- Thought leadership content
- External resources
- Can be auto-approved (future)

## Safety Features

### 1. DEV_MODE (Default: ON)
- Simulates content detection
- No action files created
- Logs to console only

### 2. DRY_RUN (Default: ON)
- Logs actions without creating files
- Safe for testing

### 3. Duplicate Detection
- Tracks content hashes in `vault/Logs/posted_content_hashes.json`
- Prevents accidental re-posting
- Persists across restarts

### 4. Content Validation
- Max length: 3000 characters
- Min length: 50 characters
- Blocks sensitive keywords: "confidential", "internal only", "password"
- Excludes drafts: "draft", "wip", "do not post"

### 5. Rate Limiting
- 3 posts per day
- 10 posts per week
- Enforced by MCP server (future)

### 6. Approval Required
- All posts require human approval
- No auto-posting
- HITL workflow enforced

## Usage

### Start Watcher

```bash
# Continuous monitoring
uv run python backend/watchers/linkedin_watcher.py

# Single check (testing)
uv run python backend/watchers/linkedin_watcher.py --once
```

### Create a Post

**Option 1: Scheduled Post (Content Calendar)**

1. Edit `vault/Content_Calendar.md`
2. Add post with format above
3. Set **Status:** to "Ready"
4. Set time within next hour
5. Watcher detects on next poll

**Option 2: Ad-hoc Post (Business Updates)**

1. Create file in `vault/Business_Updates/`
2. Add post content
3. Watcher detects on next poll

**Option 3: Announcement**

1. Create file in `vault/Announcements/`
2. Add announcement content
3. Watcher detects immediately (high priority)

### Approve Post

```bash
# List pending approvals
ls vault/Pending_Approval/

# Approve
python scripts/approve.py linkedin-q1-results-20260215T143022.md

# Reject
python scripts/reject.py linkedin-q1-results-20260215T143022.md "Content needs revision"
```

## Workflow

```
Content Source → LinkedIn Watcher → vault/Needs_Action/
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
                              MCP LinkedIn Server (Future)
                                           ↓
                                    vault/Done/
```

## Logging

### Action Logs
`vault/Logs/actions/linkedin_watcher-{date}.jsonl`

```json
{
  "timestamp": "2026-02-15T14:30:22Z",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "actor": "linkedin_watcher",
  "action_type": "post_processed",
  "target": "linkedin-q1-results-20260215T143022.md",
  "result": "success",
  "parameters": {
    "post_type": "business_update",
    "source": "Content_Calendar.md"
  }
}
```

### Posted Content Hashes
`vault/Logs/posted_content_hashes.json`

Tracks content hashes to prevent duplicates.

## Troubleshooting

### No posts detected
- Check content source files exist
- Verify **Status:** is "Ready" in Content_Calendar.md
- Check scheduled time is within next hour
- Verify no exclude keywords in content
- Check watcher logs: `vault/Logs/actions/`

### Duplicate detection false positive
- Content hash collision (rare)
- Clear hashes: `rm vault/Logs/posted_content_hashes.json`
- Restart watcher

### Posts not approved
- Check `vault/Pending_Approval/` for plans
- Use `python scripts/approve.py <filename>`
- Review plan content before approving

## Best Practices

### Content Calendar Management
- Schedule posts 1-2 weeks in advance
- Set **Status:** to "Draft" until ready
- Move posted content to Archive section
- Review calendar weekly

### Post Quality
- Keep posts under 1500 characters for better engagement
- Use 3-5 relevant hashtags
- Include visuals when possible
- Proofread before setting to "Ready"

### Posting Frequency
- Aim for 2-3 posts per week
- Avoid posting more than once per day
- Maintain consistent schedule
- Quality over quantity

### Security
- Never include sensitive information
- Review all posts before approval
- Use exclude keywords for drafts
- Keep DEV_MODE=true during testing

## Integration with Process Manager

The LinkedIn watcher runs automatically when you start all services:

```powershell
.\scripts\start.ps1
```

Check status:

```powershell
.\scripts\status.ps1
```

## Future Enhancements

1. **MCP LinkedIn Server** - Actually post to LinkedIn
2. **Image Upload** - Support media attachments
3. **Post Analytics** - Track engagement metrics
4. **Auto-scheduling** - Optimal posting times
5. **Content Suggestions** - AI-generated post ideas

## Commands

```bash
# Start watcher
uv run python backend/watchers/linkedin_watcher.py

# Single check
uv run python backend/watchers/linkedin_watcher.py --once

# View content calendar
cat vault/Content_Calendar.md

# List business updates
ls vault/Business_Updates/

# List announcements
ls vault/Announcements/

# Check posted hashes
cat vault/Logs/posted_content_hashes.json
```

## Files

```
backend/watchers/
└── linkedin_watcher.py            # Main watcher

config/
└── linkedin_config.json           # Configuration

vault/
├── Content_Calendar.md            # Scheduled posts
├── Business_Updates/              # Ad-hoc posts
├── Announcements/                 # Company announcements
└── Logs/
    ├── actions/                   # Action logs
    └── posted_content_hashes.json # Duplicate tracking

skills/linkedin-watcher/
└── SKILL.md                       # This file
```

## References

- Base Watcher: `backend/watchers/base_watcher.py`
- Gmail Watcher: `backend/watchers/gmail_watcher.py` (similar pattern)
- Calendar Watcher: `backend/watchers/calendar_watcher.py` (similar pattern)
- Orchestrator: `backend/orchestrator/main.py`
