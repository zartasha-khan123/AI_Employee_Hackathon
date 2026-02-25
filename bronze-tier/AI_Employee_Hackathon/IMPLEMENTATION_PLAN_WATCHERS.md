# LinkedIn & WhatsApp Watchers - Implementation Plan

**Date:** 2026-02-15
**Tier:** Silver+ (Enhanced)
**Status:** Awaiting Approval

---

## Executive Summary

Add 2 new watchers to the AI Employee perception layer:
1. **LinkedIn Watcher** (Required) - Monitors business update sources and creates plans for LinkedIn posting
2. **WhatsApp Watcher** (Optional) - Monitors WhatsApp messages and creates action files for responses

Both follow existing architecture patterns and integrate seamlessly with the Orchestrator.

---

## 1. LinkedIn Watcher

### Purpose

Monitor internal business update sources (content calendar, announcements) and create action files for posting to LinkedIn with human approval.

### Architecture Pattern

```
Content Source → LinkedIn Watcher → vault/Needs_Action/ → Orchestrator → Plan
                                                              ↓
                                                    vault/Pending_Approval/
                                                              ↓
                                                         [HUMAN APPROVAL]
                                                              ↓
                                                    MCP LinkedIn Server (Future)
```

### Content Sources to Monitor

1. **vault/Content_Calendar.md** - Scheduled posts with dates
2. **vault/Business_Updates/** - Folder with draft posts
3. **vault/Announcements/** - Company announcements to share

### Action File Format

```yaml
---
type: linkedin_post
id: LINKEDIN_{short_id}_{timestamp}
source: linkedin_watcher
content_source: Content_Calendar.md
post_type: business_update | announcement | article_share
scheduled_date: 2026-02-16T10:00:00Z
priority: medium
status: pending
requires_approval: true
---

## Post Content

[Post text here - max 3000 characters]

## Metadata

- **Target Audience:** Professionals, Clients, Partners
- **Hashtags:** #BusinessUpdate #Innovation
- **Media:** [Optional image/video path]
- **Link:** [Optional URL]

## Suggested Actions

- [ ] Review post content
- [ ] Approve for posting
- [ ] Schedule or post immediately
```

### Configuration

**File:** `config/linkedin_config.json`

```json
{
  "poll_interval_seconds": 600,
  "content_sources": [
    "vault/Content_Calendar.md",
    "vault/Business_Updates/",
    "vault/Announcements/"
  ],
  "post_types": {
    "business_update": {
      "max_length": 3000,
      "requires_approval": true,
      "priority": "medium"
    },
    "announcement": {
      "max_length": 3000,
      "requires_approval": true,
      "priority": "high"
    },
    "article_share": {
      "max_length": 1000,
      "requires_approval": false,
      "priority": "low"
    }
  },
  "rate_limits": {
    "posts_per_day": 3,
    "posts_per_week": 10
  },
  "exclude_keywords": ["draft", "wip", "do not post"]
}
```

### Technical Implementation

**Authentication:** LinkedIn OAuth 2.0 (for future MCP server)
- For now, watcher only reads local content sources
- No LinkedIn API calls in watcher (perception only)

**File:** `backend/watchers/linkedin_watcher.py`

**Key Methods:**
- `_scan_content_calendar()` - Parse Content_Calendar.md for scheduled posts
- `_scan_business_updates()` - Check Business_Updates/ folder for new drafts
- `_scan_announcements()` - Check Announcements/ folder
- `_parse_post_content()` - Extract post text, hashtags, media
- `_classify_post_type()` - Determine post type (update, announcement, share)
- `_check_rate_limits()` - Ensure not exceeding posting frequency

**Content Calendar Format:**

```markdown
# Content Calendar

## Scheduled Posts

### 2026-02-16 10:00 AM
**Type:** Business Update
**Status:** Ready

Excited to announce our Q1 results! Revenue up 25% YoY...

**Hashtags:** #BusinessGrowth #Q1Results
**Media:** images/q1-chart.png

---

### 2026-02-17 2:00 PM
**Type:** Article Share
**Status:** Draft

Check out this great article on AI trends...
```

### Safety Controls

1. **DEV_MODE** (default: ON) - Simulates detection, no file creation
2. **Rate Limiting** - Max 3 posts/day, 10/week
3. **Approval Required** - All posts require human approval
4. **Content Scanning** - Block posts with sensitive keywords
5. **Duplicate Detection** - Track posted content to avoid duplicates

---

## 2. WhatsApp Watcher

### Purpose

Monitor WhatsApp Web for incoming messages and create action files for important conversations requiring response.

### Architecture Pattern

```
WhatsApp Web → Playwright Automation → WhatsApp Watcher → vault/Needs_Action/
                                                                  ↓
                                                            Orchestrator
```

### Technical Approach

**Method:** WhatsApp Web automation via Playwright
- Runs headless browser
- Monitors WhatsApp Web interface
- Extracts unread messages
- No official API required (uses web interface)

**Authentication:** QR code scan (one-time setup)
- Session persists in `config/whatsapp_session/`
- Requires manual QR scan on first run

### Action File Format

```yaml
---
type: whatsapp_message
id: WHATSAPP_{short_id}_{timestamp}
source: whatsapp_watcher
from: Contact Name
phone: +1234567890
message_preview: "First 200 characters..."
received: 2026-02-15T14:30:22Z
priority: high | medium | low
status: pending
is_group: false
group_name: null
---

## Message Content

[Full message text]

## Contact Info

- **Name:** Contact Name
- **Phone:** +1234567890
- **Last Interaction:** 2026-02-10

## Suggested Actions

- [ ] Reply to message
- [ ] Mark as read
- [ ] Archive conversation
- [ ] Escalate to human
```

### Configuration

**File:** `config/whatsapp_config.json`

```json
{
  "poll_interval_seconds": 60,
  "session_path": "config/whatsapp_session",
  "headless": true,
  "priority_keywords": {
    "high": ["urgent", "asap", "emergency", "important"],
    "medium": ["question", "help", "need", "when"]
  },
  "exclude_contacts": [
    "Spam",
    "Unknown"
  ],
  "exclude_groups": true,
  "max_message_length": 5000,
  "mark_as_read": false
}
```

### Technical Implementation

**File:** `backend/watchers/whatsapp_watcher.py`

**Dependencies:**
- `playwright` - Browser automation
- `playwright-stealth` - Avoid detection

**Key Methods:**
- `_initialize_browser()` - Launch Playwright browser
- `_authenticate()` - Handle QR code scan (first time)
- `_get_unread_messages()` - Extract unread messages from WhatsApp Web
- `_parse_message()` - Extract sender, text, timestamp
- `_classify_priority()` - Determine message priority
- `_save_session()` - Persist browser session

**Browser Automation Flow:**
1. Launch headless Chrome
2. Navigate to web.whatsapp.com
3. Check if authenticated (session exists)
4. If not, display QR code for scanning
5. Wait for authentication
6. Monitor for unread messages
7. Extract message details
8. Create action files

### Safety Controls

1. **DEV_MODE** (default: ON) - Simulates detection, no browser launch
2. **Session Security** - Encrypted session storage
3. **Rate Limiting** - Max 50 messages/hour processed
4. **Privacy** - No message content logged (only metadata)
5. **Read-Only** - Never sends messages or marks as read (perception only)
6. **Group Exclusion** - Skip group chats by default

### Challenges & Mitigations

**Challenge 1:** WhatsApp Web changes UI frequently
- **Mitigation:** Use robust selectors, fallback strategies

**Challenge 2:** Session expires
- **Mitigation:** Auto-detect expiration, prompt for re-authentication

**Challenge 3:** Rate limiting by WhatsApp
- **Mitigation:** Respect polling intervals, avoid aggressive scraping

**Challenge 4:** Against WhatsApp ToS
- **Mitigation:** DEV_MODE by default, user assumes responsibility

---

## 3. Folder Structure Additions

```
AI_Employee_Hackathon/
├── backend/
│   └── watchers/
│       ├── linkedin_watcher.py          # NEW
│       └── whatsapp_watcher.py          # NEW
│
├── config/
│   ├── linkedin_config.json             # NEW
│   ├── whatsapp_config.json             # NEW
│   └── whatsapp_session/                # NEW (gitignored)
│       └── .gitkeep
│
├── skills/
│   ├── linkedin-watcher/                # NEW
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── setup_linkedin_content.py
│   └── whatsapp-watcher/                # NEW
│       ├── SKILL.md
│       └── scripts/
│           └── setup_whatsapp_auth.py
│
├── tests/
│   ├── test_linkedin_watcher.py         # NEW
│   └── test_whatsapp_watcher.py         # NEW
│
└── vault/
    ├── Content_Calendar.md              # NEW (template)
    ├── Business_Updates/                # NEW
    │   └── .gitkeep
    └── Announcements/                   # NEW
        └── .gitkeep
```

---

## 4. Process Management Integration

### Update: `backend/orchestrator/process_manager.py`

**Changes:**
- Add LinkedIn watcher initialization
- Add WhatsApp watcher initialization
- Update service count (2 → 4 watchers)

**New Environment Variables:**

```bash
# LinkedIn Watcher
LINKEDIN_CHECK_INTERVAL=600  # 10 minutes
LINKEDIN_POSTS_PER_DAY=3

# WhatsApp Watcher
WHATSAPP_CHECK_INTERVAL=60   # 1 minute
WHATSAPP_SESSION_PATH=config/whatsapp_session
WHATSAPP_HEADLESS=true
```

### Update: `scripts/start.ps1`

No changes needed - process_manager.py handles all watchers automatically.

### Update: `scripts/status.ps1`

**Changes:**
- Show LinkedIn watcher status
- Show WhatsApp watcher status
- Display total watchers: 4/4 operational

---

## 5. Security Controls

### LinkedIn Watcher Security

1. **Content Validation**
   - Max post length: 3000 characters
   - Block sensitive keywords: "confidential", "internal only", "draft"
   - Scan for PII (emails, phone numbers)

2. **Rate Limiting**
   - 3 posts per day
   - 10 posts per week
   - Enforced by safety checker

3. **Approval Required**
   - All posts require human approval
   - No auto-posting (even for low priority)

4. **Duplicate Detection**
   - Track posted content hashes
   - Prevent accidental re-posting

5. **DEV_MODE**
   - Simulates content detection
   - No action files created
   - Logs to console only

### WhatsApp Watcher Security

1. **Session Security**
   - Encrypted session storage
   - Session files in gitignore
   - Auto-expire after 30 days

2. **Privacy Protection**
   - No message content in logs
   - Only metadata tracked
   - No screenshots or recordings

3. **Read-Only Mode**
   - Never sends messages
   - Never marks as read
   - Never modifies conversations

4. **Rate Limiting**
   - Max 50 messages/hour processed
   - Prevents aggressive scraping

5. **DEV_MODE**
   - No browser launch
   - Simulates message detection
   - Safe for testing

### Global Security Updates

**Update:** `config/rate_limits.json`

```json
{
  "email": {
    "per_hour": 10,
    "per_day": 50
  },
  "linkedin": {
    "per_day": 3,
    "per_week": 10
  },
  "whatsapp": {
    "messages_per_hour": 50,
    "responses_per_day": 20
  }
}
```

---

## 6. Testing Strategy

### LinkedIn Watcher Tests

**File:** `tests/test_linkedin_watcher.py`

**Test Cases:**
1. `test_linkedin_watcher_init()` - Initialization
2. `test_scan_content_calendar()` - Parse Content_Calendar.md
3. `test_scan_business_updates()` - Detect new drafts
4. `test_parse_post_content()` - Extract post details
5. `test_classify_post_type()` - Type classification
6. `test_rate_limit_enforcement()` - Rate limiting
7. `test_duplicate_detection()` - Prevent re-posting
8. `test_create_action_file_dry_run()` - DEV_MODE
9. `test_create_action_file_real()` - Real mode
10. `test_content_validation()` - Sensitive keyword blocking

### WhatsApp Watcher Tests

**File:** `tests/test_whatsapp_watcher.py`

**Test Cases:**
1. `test_whatsapp_watcher_init()` - Initialization
2. `test_browser_initialization()` - Playwright setup (mocked)
3. `test_parse_message()` - Message extraction
4. `test_classify_priority()` - Priority classification
5. `test_exclude_groups()` - Group filtering
6. `test_exclude_contacts()` - Contact filtering
7. `test_rate_limit_enforcement()` - Rate limiting
8. `test_create_action_file_dry_run()` - DEV_MODE
9. `test_create_action_file_real()` - Real mode
10. `test_session_persistence()` - Session handling

### Integration Tests

**Test Scenarios:**

1. **LinkedIn End-to-End:**
   - Add post to Content_Calendar.md
   - LinkedIn watcher detects it
   - Action file created in Needs_Action/
   - Orchestrator creates plan
   - Plan moved to Pending_Approval/
   - Human approves
   - (Future: MCP LinkedIn server posts)

2. **WhatsApp End-to-End:**
   - Simulate incoming WhatsApp message
   - WhatsApp watcher detects it
   - Action file created in Needs_Action/
   - Orchestrator creates plan
   - Plan moved to Pending_Approval/
   - Human approves
   - (Future: MCP WhatsApp server replies)

3. **Multi-Watcher Coordination:**
   - All 4 watchers running concurrently
   - No conflicts or race conditions
   - Orchestrator handles all action files
   - Proper prioritization

### Manual Testing Checklist

**LinkedIn Watcher:**
- [ ] Setup content calendar
- [ ] Add scheduled post
- [ ] Watcher detects post
- [ ] Action file created
- [ ] Rate limiting works
- [ ] Duplicate detection works

**WhatsApp Watcher:**
- [ ] QR code authentication
- [ ] Session persistence
- [ ] Message detection
- [ ] Priority classification
- [ ] Action file created
- [ ] Privacy controls work

---

## 7. Implementation Phases

### Phase 1: LinkedIn Watcher (4-5 hours)

1. Create `backend/watchers/linkedin_watcher.py`
2. Create `config/linkedin_config.json`
3. Create `skills/linkedin-watcher/SKILL.md`
4. Create `tests/test_linkedin_watcher.py`
5. Create vault content templates
6. Update process_manager.py
7. Test end-to-end

### Phase 2: WhatsApp Watcher (5-6 hours)

1. Add Playwright dependency
2. Create `backend/watchers/whatsapp_watcher.py`
3. Create `config/whatsapp_config.json`
4. Create `skills/whatsapp-watcher/SKILL.md`
5. Create `tests/test_whatsapp_watcher.py`
6. Create authentication script
7. Update process_manager.py
8. Test end-to-end

### Phase 3: Integration & Documentation (1-2 hours)

1. Update Dashboard.md
2. Update README.md
3. Create testing guide
4. Update QUICKSTART.md
5. Final verification

**Total Effort:** 10-13 hours

---

## 8. Dependencies

### New Python Packages

```toml
# Add to pyproject.toml

[project.dependencies]
# Existing dependencies...
playwright = "^1.40.0"
playwright-stealth = "^1.0.6"
```

### Installation

```bash
# Install Playwright
uv add playwright playwright-stealth

# Install browser binaries
uv run playwright install chromium
```

---

## 9. Risks & Mitigations

### Risk 1: WhatsApp ToS Violation
**Impact:** High
**Probability:** Medium
**Mitigation:**
- DEV_MODE by default
- Clear documentation of risks
- User assumes responsibility
- Consider WhatsApp Business API alternative

### Risk 2: LinkedIn Content Quality
**Impact:** Medium
**Probability:** Low
**Mitigation:**
- Human approval required for all posts
- Content validation and scanning
- Rate limiting prevents spam

### Risk 3: Browser Automation Fragility
**Impact:** Medium
**Probability:** High
**Mitigation:**
- Robust error handling
- Fallback strategies
- Clear error messages
- Auto-retry logic

### Risk 4: Session Expiration
**Impact:** Low
**Probability:** High
**Mitigation:**
- Auto-detect expiration
- Prompt for re-authentication
- Clear instructions in SKILL.md

---

## 10. Success Criteria

### LinkedIn Watcher
- ✅ Monitors content sources (calendar, updates, announcements)
- ✅ Creates action files for scheduled posts
- ✅ Rate limiting enforced (3/day, 10/week)
- ✅ Content validation working
- ✅ Duplicate detection working
- ✅ DEV_MODE simulation working
- ✅ Unit tests passing
- ✅ Documentation complete

### WhatsApp Watcher
- ✅ Browser automation working
- ✅ QR code authentication working
- ✅ Session persistence working
- ✅ Message detection working
- ✅ Priority classification working
- ✅ Privacy controls enforced
- ✅ DEV_MODE simulation working
- ✅ Unit tests passing
- ✅ Documentation complete

### Integration
- ✅ Both watchers integrate with process_manager
- ✅ Orchestrator handles new action types
- ✅ Dashboard shows all 4 watchers
- ✅ No conflicts with existing watchers
- ✅ End-to-end workflow tested

---

## 11. Alternatives Considered

### LinkedIn Watcher Alternatives

**Alternative 1:** Monitor LinkedIn API for engagement opportunities
- **Pros:** Official API, more reliable
- **Cons:** Requires LinkedIn app approval, complex OAuth
- **Decision:** Rejected - content calendar approach simpler for MVP

**Alternative 2:** Email-based content submission
- **Pros:** No new vault structure needed
- **Cons:** Less organized, harder to schedule
- **Decision:** Rejected - content calendar more user-friendly

### WhatsApp Watcher Alternatives

**Alternative 1:** WhatsApp Business API
- **Pros:** Official, reliable, supported
- **Cons:** Requires business account, approval process, costs money
- **Decision:** Rejected - too complex for hackathon

**Alternative 2:** Third-party APIs (Twilio, etc.)
- **Pros:** Easier integration
- **Cons:** Costs money, limited features, against WhatsApp ToS
- **Decision:** Rejected - prefer free solution

**Alternative 3:** No WhatsApp integration
- **Pros:** Avoid ToS issues
- **Cons:** Missing valuable communication channel
- **Decision:** Implement with clear warnings and DEV_MODE default

---

## 12. Documentation Deliverables

1. **skills/linkedin-watcher/SKILL.md** - Complete usage guide
2. **skills/whatsapp-watcher/SKILL.md** - Complete usage guide
3. **vault/Content_Calendar.md** - Template with examples
4. **TESTING_WATCHERS.md** - Testing guide for new watchers
5. **Updated README.md** - Mention 4 watchers
6. **Updated Dashboard.md** - Show all watcher status

---

## Approval Required

Please review this implementation plan and approve before I proceed with:

1. ✅ LinkedIn Watcher implementation
2. ✅ WhatsApp Watcher implementation (optional - confirm if wanted)
3. ✅ Folder structure additions
4. ✅ Process management integration
5. ✅ Security controls
6. ✅ Testing strategy

**Questions for Clarification:**

1. **LinkedIn Content Source:** Should I implement Content_Calendar.md monitoring, or do you have a different content source in mind?

2. **WhatsApp Implementation:** Confirm you want WhatsApp watcher despite ToS concerns? Or skip it?

3. **Priority:** Implement LinkedIn first, then WhatsApp? Or both in parallel?

4. **Testing Depth:** Full unit tests for both, or focus on integration testing?

Please approve or request modifications to this plan.
