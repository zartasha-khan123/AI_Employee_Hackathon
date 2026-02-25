"""CEO Briefing Generator - creates daily executive briefings."""

from __future__ import annotations

import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from backend.briefing.aggregator import BriefingAggregator
from backend.utils.timestamps import now_iso

logger = logging.getLogger(__name__)


class BriefingGenerator:
    """Generates CEO briefings from vault data."""

    def __init__(self, vault_path: str | Path):
        """Initialize generator with vault path."""
        self.vault_path = Path(vault_path)
        self.aggregator = BriefingAggregator(vault_path)

    def generate_daily_briefing(self) -> str:
        """Generate daily CEO briefing.

        Returns:
            Markdown-formatted briefing content.
        """
        data = self.aggregator.aggregate_last_24h()

        briefing = self._format_briefing(data)

        # Save to vault
        self._save_briefing(briefing)

        return briefing

    def _format_briefing(self, data: dict[str, Any]) -> str:
        """Format aggregated data into markdown briefing."""
        now = datetime.now(UTC)
        date_str = now.strftime("%Y-%m-%d")

        lines = [
            "---",
            f"type: ceo_briefing",
            f"date: {date_str}",
            f"generated_at: {now_iso()}",
            "---",
            "",
            f"# CEO Daily Briefing - {now.strftime('%B %d, %Y')}",
            "",
            "## Executive Summary",
            "",
        ]

        # Executive summary bullets
        metrics = data["metrics"]
        summary_points = []

        if metrics["actions_completed"] > 0:
            summary_points.append(
                f"- {metrics['actions_completed']} action(s) completed in last 24 hours"
            )

        if metrics["pending_approvals"] > 0:
            summary_points.append(
                f"- {metrics['pending_approvals']} item(s) awaiting your approval"
            )

        if metrics["urgent_items"] > 0:
            summary_points.append(
                f"- {metrics['urgent_items']} urgent item(s) require attention"
            )

        if not summary_points:
            summary_points.append("- No significant activity in last 24 hours")

        lines.extend(summary_points)
        lines.extend(["", "---", ""])

        # Urgent Items section
        lines.extend(["## [!] Urgent Items", ""])

        urgent = data["urgent_items"]
        if urgent:
            for item in urgent[:5]:  # Top 5 urgent items
                lines.append(f"### {item['title']}")
                lines.append(f"- **Type:** {item['type']}")
                lines.append(f"- **Priority:** {item['priority']}")
                lines.append(f"- **Created:** {item['created']}")
                lines.append("")
        else:
            lines.append("*No urgent items*")
            lines.append("")

        lines.extend(["---", ""])

        # Pending Approvals section
        lines.extend(["## [PENDING] Approvals Needed", ""])

        pending = data["pending_approvals"]
        if pending:
            for item in pending:
                lines.append(f"- **{item['title']}** ({item['type']}) - Priority: {item['priority']}")
        else:
            lines.append("*No items pending approval*")

        lines.extend(["", "---", ""])

        # Completed Actions section
        lines.extend(["## [DONE] Completed Actions (Last 24h)", ""])

        completed = data["completed_actions"]
        if completed:
            for item in completed[:10]:  # Last 10 completed
                result_marker = "[OK]" if item["result"] == "success" else "[WARN]"
                lines.append(f"- {result_marker} **{item['title']}** ({item['type']})")
        else:
            lines.append("*No actions completed*")

        lines.extend(["", "---", ""])

        # Upcoming Events section
        lines.extend(["## [CALENDAR] Upcoming Events (Next 3 Days)", ""])

        events = data["upcoming_events"]
        if events:
            for event in events:
                lines.append(f"- {event['title']} - {event['start_time']}")
        else:
            lines.append("*No upcoming events tracked*")

        lines.extend(["", "---", ""])

        # Metrics section
        lines.extend(["## [METRICS] Activity Summary", ""])
        lines.append(f"- Actions Completed: {metrics['actions_completed']}")
        lines.append(f"- Pending Approvals: {metrics['pending_approvals']}")
        lines.append(f"- Urgent Items: {metrics['urgent_items']}")
        lines.append("")
        lines.append(f"*Generated at {metrics['timestamp']}*")

        return "\n".join(lines)

    def _save_briefing(self, content: str) -> Path:
        """Save briefing to vault/Briefings/ directory.

        Args:
            content: Markdown briefing content.

        Returns:
            Path to saved briefing file.
        """
        briefings_dir = self.vault_path / "Briefings"
        briefings_dir.mkdir(exist_ok=True)

        now = datetime.now(UTC)
        filename = f"{now.strftime('%Y-%m-%d')}-briefing.md"
        file_path = briefings_dir / filename

        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Briefing saved to {file_path}")

        return file_path


def generate_briefing(vault_path: str = "./vault") -> str:
    """Generate and save daily CEO briefing.

    Args:
        vault_path: Path to vault directory.

    Returns:
        Generated briefing content.
    """
    generator = BriefingGenerator(vault_path)
    return generator.generate_daily_briefing()


if __name__ == "__main__":
    # CLI entry point for manual briefing generation
    import sys

    vault_path = sys.argv[1] if len(sys.argv) > 1 else "./vault"

    print("Generating CEO briefing...")
    briefing = generate_briefing(vault_path)

    # Save briefing path for reference
    now = datetime.now(UTC)
    briefing_file = f"vault/Briefings/{now.strftime('%Y-%m-%d')}-briefing.md"

    print(f"\nBriefing generated successfully!")
    print(f"Saved to: {briefing_file}")
    print(f"\nPreview (first 500 chars):")
    print(briefing[:500] + "...")
