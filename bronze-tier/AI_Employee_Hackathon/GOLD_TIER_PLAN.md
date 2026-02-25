# Gold Tier Implementation Plan - Bronze-Tier Project

**Status:** Silver Tier Complete ✅ → Gold Tier In Progress 🎯

**Timeline:** 40+ hours estimated

---

## Phase 1: CEO Briefing Generator (8-10 hours)

**Priority:** HIGH | **Risk:** LOW | **Dependencies:** None

### Overview
Automated daily briefing that summarizes key information from vault for executive review.

### Implementation

**1.1 Briefing Generator Script** (`backend/briefing/generator.py`)
- Scan vault for recent activity (last 24 hours)
- Aggregate: emails, calendar events, pending approvals, completed actions
- Generate markdown briefing with sections:
  - Executive Summary (3-5 bullets)
  - Urgent Items (requires attention today)
  - Completed Actions (yesterday)
  - Upcoming Events (next 3 days)
  - Metrics (email volume, approval rate, action success rate)

**1.2 Briefing Skill** (`skills/ceo-briefing/SKILL.md`)
- Trigger: Daily at 6 AM or on-demand
- Context: Read vault/Logs/, vault/Done/, vault/Pending_Approval/
- Output: vault/Briefings/YYYY-MM-DD-briefing.md

**1.3 Scheduler Integration**
- Add to process_manager.py as daily scheduled task
- Configurable time in config/.env (BRIEFING_TIME=06:00)

**Files to Create:**
- `backend/briefing/__init__.py`
- `backend/briefing/generator.py`
- `backend/briefing/aggregator.py`
- `skills/ceo-briefing/SKILL.md`
- `skills/ceo-briefing/examples/sample-briefing.md`

**Testing:**
- Unit tests for aggregation logic
- Integration test: generate briefing from test vault data
- Manual test: review generated briefing quality

---

## Phase 2: Social Media MCP Server (10-12 hours)

**Priority:** HIGH | **Risk:** MEDIUM | **Dependencies:** LinkedIn watcher

### Overview
MCP server for posting to LinkedIn and Twitter with approval workflow.

### Implementation

**2.1 Social Media MCP Server** (`backend/mcp_servers/social_server/`)
- Tools: post_linkedin, post_twitter, schedule_post
- Safety: DEV_MODE simulation, content scanning, rate limiting (5/day/platform)
- Approval: ALWAYS requires HITL approval for public posts

**2.2 LinkedIn Posting**
- Use Playwright browser automation (same as watcher)
- Session reuse from linkedin_watcher
- Post types: text, text+image, article share
- Character limit: 3000

**2.3 Twitter Posting** (Optional for Gold, can defer to Platinum)
- Similar browser automation approach
- Character limit: 280
- Thread support for longer content

**2.4 Content Calendar Integration**
- Read from vault/Content_Calendar.md (already exists from Silver)
- Detect posts marked "Ready" and scheduled within next hour
- Create action files in vault/Needs_Action/

**Files to Create:**
- `backend/mcp_servers/social_server/__init__.py`
- `backend/mcp_servers/social_server/server.py`
- `backend/mcp_servers/social_server/linkedin_poster.py`
- `backend/mcp_servers/social_server/twitter_poster.py`
- `backend/mcp_servers/social_server/safety.py`
- `skills/social-media-poster/SKILL.md`
- `config/social_config.json`

**Testing:**
- Unit tests for content validation
- DEV_MODE test: simulate post creation
- Manual test: real LinkedIn post to test account

---

## Phase 3: Additional Skills (4-6 hours)

**Priority:** MEDIUM | **Risk:** LOW | **Dependencies:** None

### Skills to Add (need 2+ more to reach 10+)

**3.1 Invoice Drafter Skill** (`skills/invoice-drafter/`)
- Trigger: Email with "invoice request" or manual
- Context: Company_Handbook.md (billing rates, payment terms)
- Output: Draft invoice in vault/Accounting/drafts/
- Format: Markdown table with line items, totals

**3.2 Meeting Summarizer Skill** (`skills/meeting-summarizer/`)
- Trigger: Calendar event completion
- Context: Meeting notes from vault/Inbox/
- Output: Summary with action items in vault/Done/
- Format: Attendees, key decisions, action items, next steps

**3.3 Expense Tracker Skill** (`skills/expense-tracker/`)
- Trigger: Email with receipts or manual entry
- Context: Accounting/expenses/
- Output: Expense entry with category, amount, date
- Format: Structured markdown for easy aggregation

**Files to Create:**
- `skills/invoice-drafter/SKILL.md`
- `skills/meeting-summarizer/SKILL.md`
- `skills/expense-tracker/SKILL.md`
- `skills/invoice-drafter/examples/sample-invoice.md`

---

## Phase 4: Odoo Integration (12-15 hours)

**Priority:** MEDIUM | **Risk:** HIGH | **Dependencies:** Odoo instance + API access

### Overview
Integration with Odoo ERP for invoicing, CRM, and inventory management.

### Implementation

**4.1 Odoo MCP Server** (`backend/mcp_servers/odoo_server/`)
- Tools: create_invoice, update_contact, log_activity
- Authentication: API key in .env
- Rate limiting: 20 requests/hour
- Approval: Required for invoice creation, optional for CRM updates

**4.2 Odoo Client** (`backend/mcp_servers/odoo_server/odoo_client.py`)
- XML-RPC or REST API client
- Methods: authenticate, create_invoice, search_contacts, create_lead
- Error handling: connection failures, authentication errors

**4.3 Invoice Workflow**
1. Invoice drafter skill creates draft in vault
2. Human reviews and approves
3. Odoo MCP server creates invoice in Odoo
4. Invoice ID logged to vault/Accounting/

**Configuration:**
```env
ODOO_URL=https://your-instance.odoo.com
ODOO_DATABASE=your-db
ODOO_USERNAME=your-email
ODOO_API_KEY=your-key
```

**Files to Create:**
- `backend/mcp_servers/odoo_server/__init__.py`
- `backend/mcp_servers/odoo_server/server.py`
- `backend/mcp_servers/odoo_server/odoo_client.py`
- `backend/mcp_servers/odoo_server/safety.py`
- `skills/odoo-integration/SKILL.md`
- `config/odoo_config.json`

**Testing:**
- Unit tests with mocked Odoo API
- DEV_MODE test: log actions without Odoo calls
- Manual test: create test invoice in Odoo sandbox

---

## Phase 5: Payment Processing (8-10 hours)

**Priority:** LOW | **Risk:** CRITICAL | **Dependencies:** Payment provider API

### Overview
Payment processing with STRICT HITL approval and comprehensive safety controls.

### Implementation

**5.1 Payment MCP Server** (`backend/mcp_servers/payment_server/`)
- Tools: send_payment, request_payment
- Providers: Stripe, PayPal, or bank transfer
- ALWAYS requires approval (no auto-approve)
- Rate limiting: 3 transactions/hour

**5.2 Safety Controls**
- Amount limits: Max $100 without secondary approval
- Recipient allowlist: Only approved contacts
- Duplicate detection: Prevent double payments
- Audit logging: Full transaction trail
- Rollback plan: Refund instructions in approval file

**5.3 Approval Workflow**
- Payment request creates plan in vault/Plans/
- Plan includes: recipient, amount, reason, risk assessment
- Moves to vault/Pending_Approval/
- Requires explicit human approval
- Secondary confirmation for amounts > $100

**Configuration:**
```env
PAYMENT_PROVIDER=stripe
STRIPE_API_KEY=sk_test_...
PAYMENT_MAX_AMOUNT=100
PAYMENT_ALLOWLIST=vendor1@example.com,vendor2@example.com
```

**Files to Create:**
- `backend/mcp_servers/payment_server/__init__.py`
- `backend/mcp_servers/payment_server/server.py`
- `backend/mcp_servers/payment_server/stripe_client.py`
- `backend/mcp_servers/payment_server/safety.py`
- `skills/payment-processor/SKILL.md`
- `config/payment_config.json`

**Testing:**
- Unit tests with mocked payment API
- DEV_MODE test: simulate payments
- Manual test: $1 test payment in Stripe test mode

---

## Phase 6: Enhanced Logging & Monitoring (4-6 hours)

**Priority:** MEDIUM | **Risk:** LOW | **Dependencies:** None

### Implementation

**6.1 Structured Logging Enhancement**
- Add correlation IDs to all log entries
- Implement log rotation (daily, keep 90 days)
- Add performance metrics (duration, memory usage)

**6.2 Dashboard Metrics**
- Update vault/Dashboard.md with real-time stats
- Metrics: actions/day, approval rate, error rate, uptime
- Charts: Use Obsidian Dataview plugin for visualization

**6.3 Error Alerting**
- Email notification for critical errors
- Slack/Discord webhook integration (optional)
- Error summary in daily briefing

**Files to Modify:**
- `backend/utils/logging_utils.py` (enhance)
- `vault/Dashboard.md` (add metrics section)
- `backend/briefing/generator.py` (include error summary)

---

## Phase 7: Watchdog Enhancement (2-4 hours)

**Priority:** LOW | **Risk:** LOW | **Dependencies:** None

### Implementation

**7.1 Health Checks**
- Periodic health check for all services
- Restart failed services automatically
- Log service restarts to vault/Logs/system/

**7.2 Resource Monitoring**
- CPU and memory usage tracking
- Alert if usage exceeds thresholds
- Graceful shutdown on resource exhaustion

**Files to Modify:**
- `backend/orchestrator/process_manager.py` (add health checks)

---

## Implementation Order

**Week 1 (16 hours):**
1. CEO Briefing Generator (8-10 hours)
2. Additional Skills (4-6 hours)

**Week 2 (16 hours):**
3. Social Media MCP Server (10-12 hours)
4. Enhanced Logging (4-6 hours)

**Week 3 (12 hours):**
5. Odoo Integration (12-15 hours)

**Week 4 (8 hours):**
6. Payment Processing (8-10 hours)
7. Watchdog Enhancement (2-4 hours)

**Total:** 40-52 hours

---

## Success Criteria

Gold Tier is complete when:
- ✅ Daily CEO briefing generated automatically
- ✅ LinkedIn posts can be created and approved
- ✅ 10+ skills implemented
- ✅ Odoo integration functional (invoice creation)
- ✅ Payment processing with strict HITL
- ✅ Comprehensive logging with metrics
- ✅ Watchdog monitors and restarts services
- ✅ All tests passing
- ✅ Documentation updated

---

## Risk Mitigation

**High-Risk Items:**
1. Payment processing - Implement last, extensive testing in DEV_MODE
2. Odoo integration - Requires external API access, may need sandbox
3. Social media posting - ToS compliance, use test accounts first

**Rollback Plan:**
- All new features behind feature flags in config/.env
- Can disable individual MCP servers in config/mcp.json
- Vault structure unchanged, backward compatible

---

## Next Steps

1. Review and approve this plan
2. Start with Phase 1 (CEO Briefing Generator)
3. Test each phase before moving to next
4. Update README.md and constitution.md when complete
