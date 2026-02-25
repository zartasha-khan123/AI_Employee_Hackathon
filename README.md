"# AI_Employee_Hackathon" 
Gold Tier Checklist — ALL DONE:

✅ Smart content scheduling (topics → draft → approve → post)
✅ Facebook & Instagram integration
✅ Twitter/X integration
✅ Odoo Community accounting + MCP
✅ Weekly CEO Briefing generation
✅ Ralph Wiggum autonomous loop
✅ Error recovery & graceful degradation
✅ Comprehensive documentation

For hackathon submission you need:

Push to GitHub (public or private with judge access)
Record a 5-10 minute demo video (follow docs/DEMO_SCRIPT.md) (→ Watch Demo on YouTube https://youtu.be/gav99Cv0rqY)
Submit via the form: https://forms.gle/JR9T1SJq5rmQyGkGA




- - - - - - - - - - - - - - - - - - - - - - - - - - 
✅ Smart content scheduling (topics → draft → approve → post)

*Smart Content Scheduling* is the system that automatically generates social media post drafts for you daily. Here's how it works:

---

*Step 1: You define your topics ONCE*

Open vault/Content_Strategy.md in Obsidian. It already has your topics:

powershell
cat vault\Content_Strategy.md


This file contains:
- Your posting topics (AI, Backend Dev, Hackathon, Cloud, Career Tips)
- Content rules (character limits, hashtags, tone)
- Posting frequency (daily)
- What NOT to post about

*You can edit this anytime* to add/remove/change topics.

---

*Step 2: Generate a draft post*

Run this command daily (or the orchestrator does it automatically):

powershell
uv run python -m backend.scheduler.content_scheduler --generate-now --vault-path ./vault


This will:
- Read your topics from Content_Strategy.md
- Pick the next topic in rotation (won't repeat yesterday's topic)
- Generate a draft post using templates
- Save it to vault/Pending_Approval/LINKEDIN_POST_2026-02-25.md

---

*Step 3: You review and approve*

Open Obsidian → go to Pending_Approval/ → read the draft. If you like it:

powershell
# Approve and move
(Get-Content vault\Pending_Approval\LINKEDIN_POST_2026-02-25.md) -replace 'status: pending_approval', 'status: approved' | Set-Content vault\Pending_Approval\LINKEDIN_POST_2026-02-25.md
Move-Item vault\Pending_Approval\LINKEDIN_POST_2026-02-25.md vault\Approved\


Or in Obsidian, just edit the status and drag the file.

---

*Step 4: It posts automatically*

powershell
uv run python backend/actions/linkedin_poster.py --once


Or the orchestrator's action executor picks it up from /Approved and posts it.

---

*Let's try it right now!*

powershell
# Generate a draft
uv run python -m backend.scheduler.content_scheduler --generate-now --vault-path ./vault

# See what was generated
dir vault\Pending_Approval\*POST*

# Preview it
cat vault\Pending_Approval\LINKEDIN_POST_*.md


It also supports multiple platforms. Your Content_Strategy.md topics can have platform tags:


1. AI and Automation [platform: linkedin]
2. Quick dev tips [platform: twitter]
3. Behind the scenes [platform: facebook]
4. Visual demos [platform: instagram]


Want to try generating a draft right now? Run the commands above and share what it generates! 🚀
