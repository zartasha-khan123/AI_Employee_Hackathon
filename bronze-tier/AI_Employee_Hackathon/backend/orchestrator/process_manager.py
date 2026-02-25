"""Process manager - manages all AI Employee services.

This module coordinates the Gmail watcher, Calendar watcher, and Orchestrator,
running them concurrently and handling graceful shutdown.

Usage:
    uv run python backend/orchestrator/process_manager.py
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

from backend.orchestrator.main import Orchestrator
from backend.utils.health_monitor import HealthMonitor
from backend.watchers.calendar_watcher import CalendarWatcher
from backend.watchers.gmail_watcher import GmailWatcher
from backend.watchers.linkedin_watcher import LinkedInWatcher
from backend.watchers.whatsapp_watcher import WhatsAppWatcher

logger = logging.getLogger(__name__)


class ProcessManager:
    """Manages all AI Employee processes."""

    def __init__(self):
        """Initialize the process manager."""
        load_dotenv()

        # Load configuration
        self.vault_path = os.getenv("VAULT_PATH", "./vault")
        self.dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        self.dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

        # Gmail watcher config
        self.gmail_check_interval = int(os.getenv("GMAIL_CHECK_INTERVAL", "120"))
        self.gmail_credentials = os.getenv("GMAIL_CREDENTIALS_PATH", "config/credentials.json")
        self.gmail_token = os.getenv("GMAIL_TOKEN_PATH", "config/token.json")

        # Calendar watcher config
        self.calendar_check_interval = int(os.getenv("CALENDAR_CHECK_INTERVAL", "300"))
        self.calendar_credentials = os.getenv("CALENDAR_CREDENTIALS_PATH", "config/credentials.json")
        self.calendar_token = os.getenv("CALENDAR_TOKEN_PATH", "config/calendar_token.json")

        # LinkedIn watcher config
        self.linkedin_check_interval = int(os.getenv("LINKEDIN_CHECK_INTERVAL", "600"))

        # WhatsApp watcher config
        self.whatsapp_check_interval = int(os.getenv("WHATSAPP_CHECK_INTERVAL", "60"))

        # Orchestrator config
        self.orchestrator_check_interval = int(os.getenv("ORCHESTRATOR_CHECK_INTERVAL", "30"))

        # Components
        self.gmail_watcher: GmailWatcher | None = None
        self.calendar_watcher: CalendarWatcher | None = None
        self.linkedin_watcher: LinkedInWatcher | None = None
        self.whatsapp_watcher: WhatsAppWatcher | None = None
        self.orchestrator: Orchestrator | None = None
        self.health_monitor: HealthMonitor | None = None

        # Tasks
        self.tasks: list[asyncio.Task] = []
        self.service_tasks: dict[str, asyncio.Task] = {}
        self._running = False

        self.logger = logging.getLogger(__name__)

    def _initialize_components(self) -> None:
        """Initialize all components."""
        # Load Gmail config
        gmail_config_path = Path("config/gmail_config.json")
        gmail_config = {}
        if gmail_config_path.exists():
            import json
            gmail_config = json.loads(gmail_config_path.read_text(encoding="utf-8"))

        # Load Calendar config
        calendar_config_path = Path("config/calendar_config.json")
        calendar_config = {}
        if calendar_config_path.exists():
            import json
            calendar_config = json.loads(calendar_config_path.read_text(encoding="utf-8"))

        # Load LinkedIn config
        linkedin_config_path = Path("config/linkedin_config.json")
        linkedin_config = {}
        if linkedin_config_path.exists():
            import json
            linkedin_config = json.loads(linkedin_config_path.read_text(encoding="utf-8"))

        # Load WhatsApp config
        whatsapp_config_path = Path("config/whatsapp_config.json")
        whatsapp_config = {}
        if whatsapp_config_path.exists():
            import json
            whatsapp_config = json.loads(whatsapp_config_path.read_text(encoding="utf-8"))

        # Initialize Gmail watcher
        self.gmail_watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_path=self.gmail_credentials,
            token_path=self.gmail_token,
            check_interval=self.gmail_check_interval,
            gmail_config=gmail_config,
            dry_run=self.dry_run,
            dev_mode=self.dev_mode,
        )

        # Initialize Calendar watcher
        self.calendar_watcher = CalendarWatcher(
            vault_path=self.vault_path,
            credentials_path=self.calendar_credentials,
            token_path=self.calendar_token,
            check_interval=self.calendar_check_interval,
            calendar_config=calendar_config,
            dry_run=self.dry_run,
            dev_mode=self.dev_mode,
        )

        # Initialize LinkedIn watcher
        self.linkedin_watcher = LinkedInWatcher(
            vault_path=self.vault_path,
            check_interval=self.linkedin_check_interval,
            linkedin_config=linkedin_config,
            dry_run=self.dry_run,
            dev_mode=self.dev_mode,
        )

        # Initialize WhatsApp watcher
        self.whatsapp_watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            check_interval=self.whatsapp_check_interval,
            whatsapp_config=whatsapp_config,
            dry_run=self.dry_run,
            dev_mode=self.dev_mode,
        )

        # Initialize Orchestrator
        self.orchestrator = Orchestrator(
            vault_path=self.vault_path,
            check_interval=self.orchestrator_check_interval,
            dev_mode=self.dev_mode,
            dry_run=self.dry_run,
        )

        # Initialize Health Monitor
        self.health_monitor = HealthMonitor(vault_path=self.vault_path)

        self.logger.info("All components initialized")

    async def start_all(self) -> None:
        """Start all processes."""
        self._running = True
        self._initialize_components()

        self.logger.info("=" * 60)
        self.logger.info("AI EMPLOYEE - SILVER TIER")
        self.logger.info("=" * 60)
        self.logger.info("DEV_MODE: %s", self.dev_mode)
        self.logger.info("DRY_RUN: %s", self.dry_run)
        self.logger.info("Vault: %s", self.vault_path)
        self.logger.info("=" * 60)
        self.logger.info("Starting services...")
        self.logger.info("  - Gmail Watcher (interval: %ds)", self.gmail_check_interval)
        self.logger.info("  - Calendar Watcher (interval: %ds)", self.calendar_check_interval)
        self.logger.info("  - LinkedIn Watcher (interval: %ds)", self.linkedin_check_interval)
        self.logger.info("  - WhatsApp Watcher (interval: %ds)", self.whatsapp_check_interval)
        self.logger.info("  - Orchestrator (interval: %ds)", self.orchestrator_check_interval)
        self.logger.info("  - Health Monitor (interval: 60s)")
        self.logger.info("=" * 60)

        # Create tasks for each component
        gmail_task = asyncio.create_task(self._run_gmail_watcher(), name="gmail_watcher")
        calendar_task = asyncio.create_task(self._run_calendar_watcher(), name="calendar_watcher")
        linkedin_task = asyncio.create_task(self._run_linkedin_watcher(), name="linkedin_watcher")
        whatsapp_task = asyncio.create_task(self._run_whatsapp_watcher(), name="whatsapp_watcher")
        orchestrator_task = asyncio.create_task(self._run_orchestrator(), name="orchestrator")

        # Store service tasks for health monitoring
        self.service_tasks = {
            "gmail_watcher": gmail_task,
            "calendar_watcher": calendar_task,
            "linkedin_watcher": linkedin_task,
            "whatsapp_watcher": whatsapp_task,
            "orchestrator": orchestrator_task,
        }

        # Create health monitor task
        health_task = asyncio.create_task(
            self.health_monitor.monitor_loop(self.service_tasks, interval=60),
            name="health_monitor"
        )

        self.tasks = [
            gmail_task,
            calendar_task,
            linkedin_task,
            whatsapp_task,
            orchestrator_task,
            health_task,
        ]

        # Wait for all tasks
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            self.logger.info("All tasks cancelled")

    async def _run_gmail_watcher(self) -> None:
        """Run Gmail watcher with error recovery."""
        while self._running:
            try:
                await self.gmail_watcher.run()
            except Exception:
                self.logger.exception("Gmail watcher crashed, restarting in 60s...")
                await asyncio.sleep(60)

    async def _run_calendar_watcher(self) -> None:
        """Run Calendar watcher with error recovery."""
        while self._running:
            try:
                await self.calendar_watcher.run()
            except Exception:
                self.logger.exception("Calendar watcher crashed, restarting in 60s...")
                await asyncio.sleep(60)

    async def _run_linkedin_watcher(self) -> None:
        """Run LinkedIn watcher with error recovery."""
        while self._running:
            try:
                await self.linkedin_watcher.run()
            except Exception:
                self.logger.exception("LinkedIn watcher crashed, restarting in 60s...")
                await asyncio.sleep(60)

    async def _run_whatsapp_watcher(self) -> None:
        """Run WhatsApp watcher with error recovery."""
        while self._running:
            try:
                await self.whatsapp_watcher.run()
            except Exception:
                self.logger.exception("WhatsApp watcher crashed, restarting in 60s...")
                await asyncio.sleep(60)

    async def _run_orchestrator(self) -> None:
        """Run Orchestrator with error recovery."""
        while self._running:
            try:
                await self.orchestrator.run()
            except Exception:
                self.logger.exception("Orchestrator crashed, restarting in 60s...")
                await asyncio.sleep(60)

    async def stop_all(self) -> None:
        """Graceful shutdown of all processes."""
        self.logger.info("Stopping AI Employee services...")
        self._running = False

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for cancellation
        await asyncio.gather(*self.tasks, return_exceptions=True)

        # Stop orchestrator file monitor
        if self.orchestrator:
            self.orchestrator.stop()

        self.logger.info("All services stopped")


async def main() -> None:
    """Main entry point."""
    manager = ProcessManager()

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler() -> None:
        logger.info("Received shutdown signal")
        asyncio.create_task(manager.stop_all())

    # Register signal handlers (Unix-style)
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)
    else:
        # Windows doesn't support add_signal_handler
        # Use KeyboardInterrupt instead
        pass

    try:
        await manager.start_all()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        await manager.stop_all()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("AI Employee stopped")
