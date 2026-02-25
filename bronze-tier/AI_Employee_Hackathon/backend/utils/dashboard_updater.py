"""Dashboard metrics updater - updates Dashboard.md with real-time stats."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.utils.log_rotation import calculate_metrics, get_error_summary
from backend.utils.timestamps import now_iso

logger = logging.getLogger(__name__)


class DashboardUpdater:
    """Updates Dashboard.md with current system metrics."""

    def __init__(self, vault_path: str | Path):
        """Initialize dashboard updater.

        Args:
            vault_path: Path to vault directory.
        """
        self.vault_path = Path(vault_path)
        self.dashboard_path = self.vault_path / "Dashboard.md"

    def update_metrics(self) -> None:
        """Update dashboard with current metrics."""
        if not self.dashboard_path.exists():
            logger.warning("Dashboard.md not found, skipping metrics update")
            return

        # Calculate metrics
        actions_metrics = calculate_metrics(self.vault_path / "Logs" / "actions", days=7)
        recent_errors = get_error_summary(self.vault_path / "Logs" / "actions", hours=24)

        # Count pending items
        pending_count = self._count_files(self.vault_path / "Pending_Approval")
        needs_action_count = self._count_files(self.vault_path / "Needs_Action")

        # Read current dashboard
        content = self.dashboard_path.read_text(encoding="utf-8")

        # Update metrics section
        metrics_section = self._generate_metrics_section(
            actions_metrics, recent_errors, pending_count, needs_action_count
        )

        # Replace or append metrics section
        if "## System Metrics" in content:
            # Replace existing section
            parts = content.split("## System Metrics")
            before = parts[0]

            # Find next section or end of file
            after_metrics = parts[1]
            next_section_idx = after_metrics.find("\n## ")
            if next_section_idx != -1:
                after = after_metrics[next_section_idx:]
            else:
                after = ""

            new_content = before + metrics_section + after
        else:
            # Append to end
            new_content = content.rstrip() + "\n\n" + metrics_section

        # Write back
        self.dashboard_path.write_text(new_content, encoding="utf-8")
        logger.info("Dashboard metrics updated")

    def _generate_metrics_section(
        self,
        actions_metrics: dict[str, Any],
        recent_errors: list[dict[str, Any]],
        pending_count: int,
        needs_action_count: int,
    ) -> str:
        """Generate metrics section markdown."""
        lines = [
            "## System Metrics",
            "",
            f"*Last Updated: {now_iso()}*",
            "",
            "### Activity (Last 7 Days)",
            "",
            f"- **Total Actions:** {actions_metrics['total_actions']}",
            f"- **Success Rate:** {actions_metrics['success_rate']}%",
            f"- **Errors:** {actions_metrics['error_count']}",
            f"- **Avg Duration:** {actions_metrics['avg_duration_ms']} ms",
            "",
            "### Actions by Type",
            "",
        ]

        # Add action type breakdown
        for action_type, count in sorted(
            actions_metrics["actions_by_type"].items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"- **{action_type}:** {count}")

        lines.extend([
            "",
            "### Current Status",
            "",
            f"- **Pending Approval:** {pending_count} item(s)",
            f"- **Needs Action:** {needs_action_count} item(s)",
            "",
        ])

        # Add recent errors if any
        if recent_errors:
            lines.extend([
                "### Recent Errors (Last 24h)",
                "",
            ])
            for error in recent_errors[:5]:  # Show top 5
                lines.append(
                    f"- **{error['timestamp']}** - {error['actor']}: {error['action_type']} - {error['error']}"
                )
            lines.append("")

        return "\n".join(lines)

    def _count_files(self, directory: Path) -> int:
        """Count markdown files in directory."""
        if not directory.exists():
            return 0
        return len(list(directory.glob("*.md")))


def update_dashboard(vault_path: str = "./vault") -> None:
    """Update dashboard with current metrics.

    Args:
        vault_path: Path to vault directory.
    """
    updater = DashboardUpdater(vault_path)
    updater.update_metrics()


if __name__ == "__main__":
    # CLI entry point
    import sys

    vault_path = sys.argv[1] if len(sys.argv) > 1 else "./vault"
    update_dashboard(vault_path)
    print("Dashboard updated successfully")
