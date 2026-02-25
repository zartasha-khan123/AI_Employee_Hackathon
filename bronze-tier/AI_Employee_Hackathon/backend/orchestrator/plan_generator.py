"""Plan generator - invokes Claude Code to create plans from action files.

This module reads action files, loads context, and invokes Claude Code
to generate execution plans.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from backend.utils.frontmatter import parse_frontmatter
from backend.utils.timestamps import now_iso
from backend.utils.uuid_utils import short_id

logger = logging.getLogger(__name__)


class PlanGenerator:
    """Generates plans by invoking Claude Code with orchestrator skill."""

    def __init__(self, vault_path: str | Path, dev_mode: bool = True):
        self.vault_path = Path(vault_path)
        self.dev_mode = dev_mode
        self.logger = logging.getLogger(__name__)

    async def create_plan(self, action_file: Path) -> dict[str, Any]:
        self.logger.info("Generating plan for: %s", action_file.name)

        action_frontmatter = parse_frontmatter(action_file)
        action_content = action_file.read_text(encoding="utf-8")

        context_files = self._get_context_files()

        if self.dev_mode:
            plan = self._generate_mock_plan(action_frontmatter, action_content)
        else:
            plan = await self._invoke_claude_code(action_file, context_files)

        return plan

    def _get_context_files(self) -> list[Path]:
        context_files = []

        handbook = self.vault_path / "Company_Handbook.md"
        if handbook.exists():
            context_files.append(handbook)

        goals = self.vault_path / "Business_Goals.md"
        if goals.exists():
            context_files.append(goals)

        return context_files

    def _generate_mock_plan(
        self, action_frontmatter: dict[str, Any], action_content: str
    ) -> dict[str, Any]:

        # ✅ FIXED: Use action_type instead of type
        action_type = action_frontmatter.get("action_type", "unknown")
        action_id = action_frontmatter.get("action_id", "unknown")
        priority = action_frontmatter.get("priority", "medium")

        requires_approval = self._requires_approval(action_frontmatter)

        plan_id = f"PLAN_{short_id()}_{now_iso().replace(':', '').replace('-', '')[:8]}"

        frontmatter = {
            "type": "plan",
            "id": plan_id,
            "source": "orchestrator",
            "action_id": action_id,
            "action_type": action_type,
            "priority": priority,
            "status": "pending",
            "requires_approval": requires_approval,
            "created_at": now_iso(),
            "sensitivity": "medium" if requires_approval else "low",
        }

        if action_type == "email":
            body = self._generate_email_plan(action_frontmatter)
        elif action_type == "calendar_event":
            body = self._generate_calendar_plan(action_frontmatter)
        elif action_type == "linkedin_post":
            body = self._generate_linkedin_plan(action_frontmatter, action_content)
        else:
            body = self._generate_generic_plan(action_frontmatter)

        return {"frontmatter": frontmatter, "body": body}

    def _generate_email_plan(self, action_fm: dict[str, Any]) -> str:
        subject = action_fm.get("subject", "Unknown")
        from_addr = action_fm.get("from", "Unknown")

        return f"""
## Action Summary

**Type:** Email Response
**From:** {from_addr}
**Subject:** {subject}

## Proposed Action

Draft and send email response.

## Steps

1. Draft email
2. Review tone
3. Send via MCP email server
4. Log execution

## Risk Assessment

- Sensitivity: Medium
- Reversibility: Low
- Impact: Medium

## Approval Required

Yes - external communication

## Rollback Plan

Send correction email if necessary.
"""

    def _generate_calendar_plan(self, action_fm: dict[str, Any]) -> str:
        summary = action_fm.get("summary", "Unknown")
        start_time = action_fm.get("start_time", "Unknown")

        return f"""
## Action Summary

**Type:** Calendar Event
**Event:** {summary}
**Start Time:** {start_time}

## Proposed Action

Create calendar event.

## Steps

1. Validate time
2. Add attendees
3. Create event
4. Send invites

## Risk Assessment

- Sensitivity: Medium
- Reversibility: Medium
- Impact: Medium

## Approval Required

Yes - scheduling impact

## Rollback Plan

Delete or update event.
"""

    def _generate_linkedin_plan(self, action_fm: dict[str, Any], content: str) -> str:
        return f"""
## Action Summary

**Type:** LinkedIn Post
**Action ID:** {action_fm.get("action_id", "unknown")}

## Proposed Action

Publish LinkedIn update with provided content.

## Steps

1. Review post content
2. Optimize formatting
3. Post via LinkedIn MCP integration
4. Log post URL

## Risk Assessment

- Sensitivity: Medium (public communication)
- Reversibility: Low (public visibility)
- Impact: High (brand exposure)

## Approval Required

Yes - public-facing communication

## Rollback Plan

If incorrect:
1. Edit post immediately
2. Publish clarification comment
3. Log incident
"""

    def _generate_generic_plan(self, action_fm: dict[str, Any]) -> str:

        # ✅ FIXED: use correct keys
        action_type = action_fm.get("action_type", "unknown")
        action_id = action_fm.get("action_id", "unknown")

        return f"""
## Action Summary

**Type:** {action_type}
**ID:** {action_id}

## Proposed Action

Review and determine appropriate action.

## Steps

1. Analyze content
2. Determine execution path
3. Execute or escalate

## Risk Assessment

- Sensitivity: Unknown
- Reversibility: Unknown
- Impact: Unknown

## Approval Required

Yes - unknown action type requires review

## Rollback Plan

Manual intervention required.
"""

    def _requires_approval(self, action_frontmatter: dict[str, Any]) -> bool:

        # ✅ FIXED
        action_type = action_frontmatter.get("action_type", "unknown")
        priority = action_frontmatter.get("priority", "medium")

        if priority == "high":
            return True

        if action_type in ["email", "calendar_event", "linkedin_post"]:
            return True

        return True

    async def _invoke_claude_code(
        self, action_file: Path, context_files: list[Path]
    ) -> dict[str, Any]:

        cmd = ["claude-code", "--skill", "orchestrator"]
        cmd.extend(["--context", str(action_file)])

        for ctx_file in context_files:
            cmd.extend(["--context", str(ctx_file)])

        output_dir = self.vault_path / "Plans"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"plan-{action_file.stem}-{now_iso().replace(':', '')[:8]}.md"
        cmd.extend(["--output", str(output_file)])

        self.logger.info("Invoking Claude Code")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )

        if output_file.exists():
            plan_frontmatter = parse_frontmatter(output_file)
            plan_content = output_file.read_text(encoding="utf-8")

            from backend.utils.frontmatter import extract_frontmatter
            _, body = extract_frontmatter(plan_content)

            return {"frontmatter": plan_frontmatter, "body": body}

        raise FileNotFoundError("Claude Code did not generate plan")