"""CEO Briefing Generator - aggregates vault activity into executive summary."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any

from backend.utils.frontmatter import extract_frontmatter
from backend.utils.timestamps import now_iso

logger = logging.getLogger(__name__)


class BriefingAggregator:
    """Aggregates data from vault for CEO briefing."""

    def __init__(self, vault_path: str | Path):
        """Initialize aggregator with vault path."""
        self.vault_path = Path(vault_path)

    def aggregate_last_24h(self) -> dict[str, Any]:
        """Aggregate all vault activity from last 24 hours.

        Returns:
            Dictionary with aggregated data:
            - urgent_items: List of items requiring attention
            - completed_actions: List of completed actions
            - pending_approvals: List of items awaiting approval
            - upcoming_events: List of calendar events (next 3 days)
            - metrics: Activity metrics
        """
        cutoff = datetime.now(UTC) - timedelta(hours=24)

        return {
            "urgent_items": self._get_urgent_items(),
            "completed_actions": self._get_completed_actions(cutoff),
            "pending_approvals": self._get_pending_approvals(),
            "upcoming_events": self._get_upcoming_events(),
            "metrics": self._calculate_metrics(cutoff),
        }

    def _get_urgent_items(self) -> list[dict[str, Any]]:
        """Get items marked as urgent or high priority."""
        urgent = []
        needs_action_dir = self.vault_path / "Needs_Action"

        if not needs_action_dir.exists():
            return urgent

        for file_path in needs_action_dir.glob("*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")
                frontmatter, _ = extract_frontmatter(content)

                priority = frontmatter.get("priority", "medium")
                if priority == "high":
                    urgent.append({
                        "title": file_path.stem,
                        "type": frontmatter.get("type", "unknown"),
                        "priority": priority,
                        "created": frontmatter.get("created_at", "unknown"),
                    })
            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")

        return sorted(urgent, key=lambda x: x.get("created", ""), reverse=True)

    def _get_completed_actions(self, cutoff: datetime) -> list[dict[str, Any]]:
        """Get actions completed since cutoff time."""
        completed = []
        done_dir = self.vault_path / "Done"

        if not done_dir.exists():
            return completed

        for file_path in done_dir.glob("*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")
                frontmatter, _ = extract_frontmatter(content)

                completed_at = frontmatter.get("completed_at")
                if completed_at:
                    # Parse ISO timestamp
                    completed_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                    if completed_dt >= cutoff:
                        completed.append({
                            "title": file_path.stem,
                            "type": frontmatter.get("type", "unknown"),
                            "completed_at": completed_at,
                            "result": frontmatter.get("execution_result", "success"),
                        })
            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")

        return sorted(completed, key=lambda x: x.get("completed_at", ""), reverse=True)

    def _get_pending_approvals(self) -> list[dict[str, Any]]:
        """Get items awaiting human approval."""
        pending = []
        pending_dir = self.vault_path / "Pending_Approval"

        if not pending_dir.exists():
            return pending

        for file_path in pending_dir.glob("*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")
                frontmatter, _ = extract_frontmatter(content)

                pending.append({
                    "title": file_path.stem,
                    "type": frontmatter.get("type", "unknown"),
                    "priority": frontmatter.get("priority", "medium"),
                    "created": frontmatter.get("pending_at", "unknown"),
                })
            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")

        return sorted(pending, key=lambda x: x.get("priority"), reverse=True)

    def _get_upcoming_events(self) -> list[dict[str, Any]]:
        """Get calendar events for next 3 days."""
        events = []
        # This would integrate with calendar watcher data
        # For now, return empty list - can be enhanced later
        return events

    def _calculate_metrics(self, cutoff: datetime) -> dict[str, Any]:
        """Calculate activity metrics since cutoff."""
        return {
            "actions_completed": len(self._get_completed_actions(cutoff)),
            "pending_approvals": len(self._get_pending_approvals()),
            "urgent_items": len(self._get_urgent_items()),
            "timestamp": now_iso(),
        }
