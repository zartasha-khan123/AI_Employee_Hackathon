"""Workflow manager for moving files through vault folders.

This module handles file transitions between vault folders and updates
frontmatter status fields.
"""

import logging
import shutil
from pathlib import Path
from typing import Any

from backend.utils.frontmatter import parse_frontmatter, update_frontmatter
from backend.utils.logging_utils import log_action
from backend.utils.timestamps import now_iso
from backend.utils.uuid_utils import correlation_id

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Manages file workflow through vault folders."""

    def __init__(self, vault_path: str | Path):
        """Initialize the workflow manager.

        Args:
            vault_path: Path to the vault directory.
        """
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.plans = self.vault_path / "Plans"
        self.pending_approval = self.vault_path / "Pending_Approval"
        self.approved = self.vault_path / "Approved"
        self.rejected = self.vault_path / "Rejected"
        self.done = self.vault_path / "Done"
        self.logs_path = self.vault_path / "Logs"
        self.logger = logging.getLogger(__name__)

        # Ensure all folders exist
        for folder in [
            self.needs_action,
            self.plans,
            self.pending_approval,
            self.approved,
            self.rejected,
            self.done,
            self.logs_path,
        ]:
            folder.mkdir(parents=True, exist_ok=True)

    def move_to_plans(self, source_file: Path, plan_content: dict[str, Any]) -> Path:
        """Move action file to Plans folder with plan content.

        Args:
            source_file: Original action file path.
            plan_content: Plan data including frontmatter and body.

        Returns:
            Path to the new plan file.
        """
        # Generate plan filename
        plan_filename = f"plan-{source_file.stem}-{now_iso().replace(':', '').replace('-', '')[:8]}.md"
        plan_path = self.plans / plan_filename

        # Create plan file
        from backend.utils.frontmatter import create_file_with_frontmatter

        create_file_with_frontmatter(
            plan_path, plan_content["frontmatter"], plan_content["body"]
        )

        self.logger.info("Created plan: %s", plan_filename)

        # Log action
        log_action(
            self.logs_path / "workflow",
            {
                "timestamp": now_iso(),
                "correlation_id": correlation_id(),
                "actor": "workflow_manager",
                "action_type": "plan_created",
                "source": str(source_file.name),
                "target": plan_filename,
                "result": "success",
            },
        )

        return plan_path

    def move_to_pending_approval(self, plan_file: Path) -> Path:
        """Move plan to Pending_Approval folder.

        Args:
            plan_file: Plan file path.

        Returns:
            Path to the moved file.
        """
        dest_path = self.pending_approval / plan_file.name

        # Update frontmatter
        update_frontmatter(plan_file, {"status": "pending_approval", "pending_at": now_iso()})

        # Move file
        shutil.move(str(plan_file), str(dest_path))

        self.logger.info("Moved to pending approval: %s", plan_file.name)

        # Log action
        log_action(
            self.logs_path / "workflow",
            {
                "timestamp": now_iso(),
                "correlation_id": correlation_id(),
                "actor": "workflow_manager",
                "action_type": "moved_to_pending_approval",
                "target": plan_file.name,
                "result": "success",
            },
        )

        return dest_path

    def move_to_approved(self, plan_file: Path) -> Path:
        """Move plan to Approved folder (auto-approved or human-approved).

        Args:
            plan_file: Plan file path.

        Returns:
            Path to the moved file.
        """
        dest_path = self.approved / plan_file.name

        # Update frontmatter
        update_frontmatter(plan_file, {"status": "approved", "approved_at": now_iso()})

        # Move file
        shutil.move(str(plan_file), str(dest_path))

        self.logger.info("Moved to approved: %s", plan_file.name)

        # Log action
        log_action(
            self.logs_path / "workflow",
            {
                "timestamp": now_iso(),
                "correlation_id": correlation_id(),
                "actor": "workflow_manager",
                "action_type": "moved_to_approved",
                "target": plan_file.name,
                "result": "success",
            },
        )

        return dest_path

    def approve_plan(self, plan_filename: str, approved_by: str = "human") -> Path:
        """Approve a pending plan (called by approval CLI).

        Args:
            plan_filename: Name of the plan file in Pending_Approval.
            approved_by: Who approved the plan.

        Returns:
            Path to the approved file.
        """
        source_path = self.pending_approval / plan_filename

        if not source_path.exists():
            raise FileNotFoundError(f"Plan not found: {plan_filename}")

        dest_path = self.approved / plan_filename

        # Update frontmatter
        update_frontmatter(
            source_path,
            {"status": "approved", "approved_at": now_iso(), "approved_by": approved_by},
        )

        # Move file
        shutil.move(str(source_path), str(dest_path))

        self.logger.info("Plan approved by %s: %s", approved_by, plan_filename)

        # Log action
        log_action(
            self.logs_path / "audit",
            {
                "timestamp": now_iso(),
                "correlation_id": correlation_id(),
                "actor": approved_by,
                "action_type": "plan_approved",
                "target": plan_filename,
                "result": "success",
            },
        )

        return dest_path

    def reject_plan(self, plan_filename: str, reason: str, rejected_by: str = "human") -> Path:
        """Reject a pending plan (called by rejection CLI).

        Args:
            plan_filename: Name of the plan file in Pending_Approval.
            reason: Reason for rejection.
            rejected_by: Who rejected the plan.

        Returns:
            Path to the rejected file.
        """
        source_path = self.pending_approval / plan_filename

        if not source_path.exists():
            raise FileNotFoundError(f"Plan not found: {plan_filename}")

        dest_path = self.rejected / plan_filename

        # Update frontmatter
        update_frontmatter(
            source_path,
            {
                "status": "rejected",
                "rejected_at": now_iso(),
                "rejected_by": rejected_by,
                "rejection_reason": reason,
            },
        )

        # Move file
        shutil.move(str(source_path), str(dest_path))

        self.logger.info("Plan rejected by %s: %s (reason: %s)", rejected_by, plan_filename, reason)

        # Log action
        log_action(
            self.logs_path / "audit",
            {
                "timestamp": now_iso(),
                "correlation_id": correlation_id(),
                "actor": rejected_by,
                "action_type": "plan_rejected",
                "target": plan_filename,
                "reason": reason,
                "result": "success",
            },
        )

        return dest_path

    def move_to_done(self, approved_file: Path, execution_result: dict[str, Any]) -> Path:
        """Move executed plan to Done folder.

        Args:
            approved_file: Approved plan file path.
            execution_result: Result of plan execution.

        Returns:
            Path to the done file.
        """
        dest_path = self.done / approved_file.name

        # Update frontmatter
        update_frontmatter(
            approved_file,
            {
                "status": "completed",
                "completed_at": now_iso(),
                "execution_result": execution_result.get("status", "unknown"),
            },
        )

        # Move file
        shutil.move(str(approved_file), str(dest_path))

        self.logger.info("Moved to done: %s", approved_file.name)

        # Log action
        log_action(
            self.logs_path / "workflow",
            {
                "timestamp": now_iso(),
                "correlation_id": correlation_id(),
                "actor": "workflow_manager",
                "action_type": "moved_to_done",
                "target": approved_file.name,
                "execution_result": execution_result,
                "result": "success",
            },
        )

        return dest_path

    def process_approval_decisions(self) -> list[Path]:
        """Check for human approval decisions (files moved manually).

        Returns:
            List of newly approved plan files.
        """
        # This is a placeholder for detecting manual file moves
        # In practice, users will use approve.py/reject.py scripts
        return []

    def get_pending_approvals(self) -> list[Path]:
        """Get list of plans awaiting approval.

        Returns:
            List of plan file paths in Pending_Approval.
        """
        if not self.pending_approval.exists():
            return []

        return sorted(self.pending_approval.glob("*.md"))

    def get_approved_plans(self) -> list[Path]:
        """Get list of approved plans ready for execution.

        Returns:
            List of plan file paths in Approved.
        """
        if not self.approved.exists():
            return []

        return sorted(self.approved.glob("*.md"))
