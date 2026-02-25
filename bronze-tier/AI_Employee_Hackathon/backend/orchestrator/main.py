"""Main orchestrator - the reasoning layer of the AI Employee.

The orchestrator monitors the vault for new action files, generates plans,
routes them for approval, and manages execution.

Usage:
    # Start orchestrator
    uv run python backend/orchestrator/main.py

    # Single cycle (for testing)
    uv run python backend/orchestrator/main.py --once
"""

import argparse
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from backend.orchestrator.file_monitor import FileMonitor
from backend.orchestrator.plan_generator import PlanGenerator
from backend.orchestrator.workflow_manager import WorkflowManager
from backend.utils.logging_utils import log_action
from backend.utils.timestamps import now_iso
from backend.utils.uuid_utils import correlation_id

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main orchestrator that coordinates perception, reasoning, and action."""

    def __init__(
        self,
        vault_path: str | Path,
        check_interval: int = 30,
        dev_mode: bool = True,
        dry_run: bool = True,
    ):
        """Initialize the orchestrator.

        Args:
            vault_path: Path to the vault directory.
            check_interval: Seconds between checks for new files.
            dev_mode: If True, simulates plan generation.
            dry_run: If True, logs actions without executing.
        """
        self.vault_path = Path(vault_path)
        self.check_interval = check_interval
        self.dev_mode = dev_mode
        self.dry_run = dry_run

        self.file_monitor = FileMonitor(vault_path)
        self.plan_generator = PlanGenerator(vault_path, dev_mode=dev_mode)
        self.workflow_manager = WorkflowManager(vault_path)

        self.logs_path = self.vault_path / "Logs"
        self.logger = logging.getLogger(__name__)

        self._running = False
        self._processed_files = set()

    async def run(self) -> None:
        """Main orchestration loop."""
        self._running = True
        self.logger.info(
            "Starting orchestrator (interval: %ds, dev_mode: %s, dry_run: %s)",
            self.check_interval,
            self.dev_mode,
            self.dry_run,
        )

        # Process existing files first
        await self._process_existing_files()

        # Start file monitor
        self.file_monitor.start(self._on_new_action_file)

        try:
            while self._running:
                # Check for approved plans ready for execution
                await self._process_approved_plans()

                # Sleep until next check
                await asyncio.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.logger.info("Orchestrator interrupted by user")
        finally:
            self.file_monitor.stop()
            self.logger.info("Orchestrator stopped")

    async def run_once(self) -> None:
        """Run a single orchestration cycle (for testing)."""
        self.logger.info("Running single orchestration cycle")

        # Process existing files
        await self._process_existing_files()

        # Process approved plans
        await self._process_approved_plans()

        self.logger.info("Single cycle complete")

    async def _process_existing_files(self) -> None:
        """Process any existing action files in Needs_Action."""
        existing_files = self.file_monitor.get_existing_files()

        if not existing_files:
            self.logger.debug("No existing action files found")
            return

        self.logger.info("Processing %d existing action files", len(existing_files))

        for action_file in existing_files:
            if str(action_file) not in self._processed_files:
                await self._process_action_file(action_file)

    def _on_new_action_file(self, action_file: Path) -> None:
        """Callback when new action file is detected.

        Args:
            action_file: Path to the new action file.
        """
        # Run async processing in event loop
        asyncio.create_task(self._process_action_file(action_file))

    async def _process_action_file(self, action_file: Path) -> None:
        """Process a single action file.

        Args:
            action_file: Path to the action file.
        """
        if str(action_file) in self._processed_files:
            return

        self._processed_files.add(str(action_file))

        try:
            self.logger.info("Processing action file: %s", action_file.name)

            # Generate plan
            plan = await self.plan_generator.create_plan(action_file)

            # Create plan file
            plan_file = self.workflow_manager.move_to_plans(action_file, plan)

            # Determine if approval required
            requires_approval = plan["frontmatter"].get("requires_approval", True)

            if requires_approval:
                # Move to pending approval
                self.workflow_manager.move_to_pending_approval(plan_file)
                self.logger.info(
                    "Plan requires approval: %s (moved to Pending_Approval)", plan_file.name
                )
            else:
                # Auto-approve
                self.workflow_manager.move_to_approved(plan_file)
                self.logger.info("Plan auto-approved: %s (moved to Approved)", plan_file.name)

            # Log decision
            log_action(
                self.logs_path / "decisions",
                {
                    "timestamp": now_iso(),
                    "correlation_id": correlation_id(),
                    "actor": "orchestrator",
                    "action_type": "plan_created",
                    "source": action_file.name,
                    "target": plan_file.name,
                    "requires_approval": requires_approval,
                    "result": "success",
                },
            )

        except Exception as e:
            self.logger.exception("Error processing action file: %s", action_file.name)
            log_action(
                self.logs_path / "errors",
                {
                    "timestamp": now_iso(),
                    "correlation_id": correlation_id(),
                    "actor": "orchestrator",
                    "action_type": "process_action_file",
                    "target": action_file.name,
                    "error": str(e),
                    "result": "failure",
                },
            )

    async def _process_approved_plans(self) -> None:
        """Process approved plans ready for execution."""
        approved_plans = self.workflow_manager.get_approved_plans()

        if not approved_plans:
            return

        self.logger.info("Processing %d approved plans", len(approved_plans))

        for plan_file in approved_plans:
            await self._execute_plan(plan_file)

    async def _execute_plan(self, plan_file: Path) -> None:
        """Execute an approved plan.

        Args:
            plan_file: Path to the approved plan file.
        """
        try:
            self.logger.info("Executing plan: %s", plan_file.name)

            if self.dry_run:
                # Simulate execution
                execution_result = {
                    "status": "simulated",
                    "message": "Dry run - no actual execution",
                }
                self.logger.info("[DRY RUN] Would execute plan: %s", plan_file.name)
            else:
                # TODO: Implement actual execution via MCP servers
                execution_result = {
                    "status": "pending",
                    "message": "MCP execution not yet implemented",
                }

            # Move to done
            self.workflow_manager.move_to_done(plan_file, execution_result)

            # Log execution
            log_action(
                self.logs_path / "executions",
                {
                    "timestamp": now_iso(),
                    "correlation_id": correlation_id(),
                    "actor": "orchestrator",
                    "action_type": "plan_executed",
                    "target": plan_file.name,
                    "execution_result": execution_result,
                    "result": "success",
                },
            )

        except Exception as e:
            self.logger.exception("Error executing plan: %s", plan_file.name)
            log_action(
                self.logs_path / "errors",
                {
                    "timestamp": now_iso(),
                    "correlation_id": correlation_id(),
                    "actor": "orchestrator",
                    "action_type": "execute_plan",
                    "target": plan_file.name,
                    "error": str(e),
                    "result": "failure",
                },
            )

    def stop(self) -> None:
        """Stop the orchestrator gracefully."""
        self._running = False


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Orchestrator - AI Employee Reasoning Layer")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle and exit",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the orchestrator."""
    load_dotenv()
    args = _parse_args(argv)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    vault_path = os.getenv("VAULT_PATH", "./vault")
    check_interval = int(os.getenv("ORCHESTRATOR_CHECK_INTERVAL", "30"))
    dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

    orchestrator = Orchestrator(
        vault_path=vault_path,
        check_interval=check_interval,
        dev_mode=dev_mode,
        dry_run=dry_run,
    )

    if args.once:
        asyncio.run(orchestrator.run_once())
    else:
        asyncio.run(orchestrator.run())


if __name__ == "__main__":
    main()
