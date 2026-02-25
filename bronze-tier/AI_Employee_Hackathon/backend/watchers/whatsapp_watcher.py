"""WhatsApp watcher - monitors WhatsApp Web for messages.

⚠️ WARNING: This watcher uses WhatsApp Web automation which may violate
WhatsApp's Terms of Service. Use at your own risk. DEV_MODE is enabled
by default to prevent actual browser automation.

This is a PERCEPTION layer component. It observes WhatsApp Web and creates
action files for messages. It never sends messages or marks as read.

Usage:
    # Continuous polling (requires authentication first)
    uv run python backend/watchers/whatsapp_watcher.py

    # Single check
    uv run python backend/watchers/whatsapp_watcher.py --once

    # Setup authentication (QR code scan)
    uv run python skills/whatsapp-watcher/scripts/setup_whatsapp_auth.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from backend.utils.frontmatter import create_file_with_frontmatter
from backend.utils.logging_utils import log_action
from backend.utils.timestamps import format_filename_timestamp, now_iso
from backend.utils.uuid_utils import correlation_id, short_id
from backend.watchers.base_watcher import BaseWatcher

logger = logging.getLogger(__name__)


def _slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a filename-safe slug."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:max_length].rstrip("-")


def _load_whatsapp_config(config_path: str = "config/whatsapp_config.json") -> dict[str, Any]:
    """Load WhatsApp configuration from JSON file."""
    path = Path(config_path)
    if not path.exists():
        logger.warning("WhatsApp config not found at %s, using defaults", config_path)
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


class WhatsAppWatcher(BaseWatcher):
    """Watches WhatsApp Web for messages and creates vault action files."""

    def __init__(
        self,
        vault_path: str,
        check_interval: int = 60,
        whatsapp_config: dict[str, Any] | None = None,
        dry_run: bool = True,
        dev_mode: bool = True,
    ):
        super().__init__(vault_path, check_interval)
        self.whatsapp_config = whatsapp_config or {}
        self.dry_run = dry_run
        self.dev_mode = dev_mode
        self.session_path = Path(self.whatsapp_config.get("session_path", "config/whatsapp_session"))
        self.headless = self.whatsapp_config.get("headless", True)
        self.browser = None
        self.page = None
        self.processed_ids_path = self.logs_path / "processed_messages.json"
        self._processed_ids: set[str] = set()
        self._consecutive_errors = 0

    # ── Browser Management ─────────────────────────────────────────

    async def _initialize_browser(self) -> None:
        """Initialize Playwright browser.

        Note: Only called when dev_mode=False.
        """
        if self.dev_mode:
            self.logger.info("[DEV MODE] Skipping browser initialization")
            return

        try:
            from playwright.async_api import async_playwright

            self.logger.info("Initializing Playwright browser...")

            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )

            # Load or create context with session
            state_file = self.session_path / "state.json"
            if state_file.exists():
                context = await self.browser.new_context(
                    storage_state=str(state_file)
                )
            else:
                context = await self.browser.new_context()

            self.page = await context.new_page()
            await self.page.goto("https://web.whatsapp.com")

            self.logger.info("Browser initialized successfully")

        except ImportError:
            self.logger.error("Playwright not installed. Run: uv add playwright")
            raise
        except Exception as e:
            self.logger.exception("Failed to initialize browser")
            raise

    async def _check_authentication(self) -> bool:
        """Check if WhatsApp Web is authenticated.

        Returns:
            True if authenticated, False if QR code scan needed.
        """
        if self.dev_mode:
            return True  # Simulate authenticated in dev mode

        try:
            # Wait for either QR code or chat list
            await self.page.wait_for_selector(
                'div[data-testid="chat-list"], canvas[aria-label="Scan me!"]',
                timeout=10000,
            )

            # Check if QR code is present
            qr_code = await self.page.query_selector('canvas[aria-label="Scan me!"]')

            if qr_code:
                self.logger.warning("WhatsApp Web not authenticated. QR code scan required.")
                self.logger.warning(
                    "Run: uv run python skills/whatsapp-watcher/scripts/setup_whatsapp_auth.py"
                )
                return False

            return True

        except Exception as e:
            self.logger.error("Error checking authentication: %s", e)
            return False

    async def _save_session(self) -> None:
        """Save browser session for persistence."""
        if self.dev_mode or not self.page:
            return

        try:
            self.session_path.mkdir(parents=True, exist_ok=True)
            await self.page.context.storage_state(path=str(self.session_path / "state.json"))
            self.logger.info("Session saved successfully")
        except Exception as e:
            self.logger.error("Failed to save session: %s", e)

    # ── Message Processing ─────────────────────────────────────────

    def _load_processed_ids(self) -> None:
        """Load processed message IDs from disk."""
        if not self.processed_ids_path.exists():
            self._processed_ids = set()
            return

        try:
            data = json.loads(self.processed_ids_path.read_text(encoding="utf-8"))
            self._processed_ids = set(data.get("processed_ids", []))
        except (json.JSONDecodeError, KeyError):
            self.logger.warning("Corrupted processed_messages.json, starting fresh")
            self._processed_ids = set()

    def _save_processed_ids(self) -> None:
        """Save processed message IDs to disk."""
        self.processed_ids_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"processed_ids": list(self._processed_ids), "updated_at": now_iso()}
        self.processed_ids_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    async def _get_unread_messages(self) -> list[dict[str, Any]]:
        """Extract unread messages from WhatsApp Web.

        Returns:
            List of message dicts ready for action file creation.
        """
        if self.dev_mode:
            # Simulate finding messages in dev mode
            self.logger.info("[DEV MODE] Simulating message detection")
            return []

        if not self.page:
            return []

        try:
            messages = []

            # Find unread chats (with unread badge)
            unread_chats = await self.page.query_selector_all(
                'div[data-testid="cell-frame-container"]:has(span[data-testid="icon-unread-count"])'
            )

            for chat in unread_chats[:10]:  # Limit to 10 chats
                try:
                    # Click chat to open
                    await chat.click()
                    await asyncio.sleep(1)

                    # Get contact name
                    contact_elem = await self.page.query_selector('span[data-testid="conversation-info-header-chat-title"]')
                    contact_name = await contact_elem.inner_text() if contact_elem else "Unknown"

                    # Check if group (skip if configured)
                    if self.whatsapp_config.get("exclude_groups", True):
                        is_group = await self.page.query_selector('span[data-testid="default-group"]')
                        if is_group:
                            continue

                    # Get last message
                    message_elems = await self.page.query_selector_all('div[data-testid="msg-container"]')
                    if not message_elems:
                        continue

                    last_message = message_elems[-1]
                    message_text_elem = await last_message.query_selector('span.selectable-text')
                    message_text = await message_text_elem.inner_text() if message_text_elem else ""

                    # Generate message ID
                    message_id = f"{contact_name}_{message_text[:50]}"

                    # Skip if already processed
                    if message_id in self._processed_ids:
                        continue

                    # Classify priority
                    priority = self._classify_priority(message_text)

                    messages.append(
                        {
                            "message_id": message_id,
                            "from": contact_name,
                            "message": message_text[:self.whatsapp_config.get("max_message_length", 5000)],
                            "priority": priority,
                            "is_group": False,
                            "received": now_iso(),
                        }
                    )

                except Exception as e:
                    self.logger.error("Error processing chat: %s", e)
                    continue

            return messages

        except Exception as e:
            self.logger.exception("Error getting unread messages")
            return []

    def _classify_priority(self, message_text: str) -> str:
        """Classify message priority based on keywords."""
        text_lower = message_text.lower()
        priority_keywords = self.whatsapp_config.get("priority_keywords", {})

        for kw in priority_keywords.get("high", []):
            if kw in text_lower:
                return "high"

        for kw in priority_keywords.get("medium", []):
            if kw in text_lower:
                return "medium"

        return "low"

    # ── Main Check Method ──────────────────────────────────────────

    async def check_for_updates(self) -> list[dict[str, Any]]:
        """Poll WhatsApp Web for new messages.

        Returns:
            List of message dicts that need action files created.
        """
        self._load_processed_ids()

        if self.dev_mode:
            # In dev mode, simulate detection
            self.logger.info("[DEV MODE] Simulating WhatsApp message check")
            return []

        try:
            # Initialize browser if needed
            if not self.browser:
                await self._initialize_browser()

            # Check authentication
            if not await self._check_authentication():
                return []

            # Get unread messages
            messages = await self._get_unread_messages()

            self._consecutive_errors = 0
            return messages

        except Exception:
            self._consecutive_errors += 1
            self.logger.exception(
                "Error checking WhatsApp messages (consecutive errors: %d)",
                self._consecutive_errors,
            )
            return []

    # ── Action File Creation ───────────────────────────────────────

    async def create_action_file(self, item: dict[str, Any]) -> Path | None:
        """Create a markdown action file in Needs_Action for a WhatsApp message.

        Args:
            item: Parsed message dict from check_for_updates.

        Returns:
            Path to created file, or None if dry_run.
        """
        from_slug = _slugify(item["from"])
        timestamp = format_filename_timestamp()
        filename = f"whatsapp-{from_slug}-{timestamp}.md"
        file_path = self.needs_action / filename

        message_id = f"WHATSAPP_{short_id()}_{timestamp}"

        frontmatter: dict[str, Any] = {
            "type": "whatsapp_message",
            "id": message_id,
            "source": "whatsapp_watcher",
            "from": item["from"],
            "message_preview": item["message"][:200],
            "received": item["received"],
            "priority": item["priority"],
            "status": "pending",
            "is_group": item.get("is_group", False),
        }

        body = f"""
## Message Content

{item["message"]}

## Contact Info

- **From:** {item["from"]}
- **Received:** {item["received"]}
- **Priority:** {item["priority"]}

## Suggested Actions

- [ ] Reply to message
- [ ] Mark as read
- [ ] Archive conversation
- [ ] Escalate to human
"""

        cid = correlation_id()

        if self.dry_run:
            self.logger.info(
                "[DRY RUN] Would create action file: %s (priority: %s, from: %s)",
                filename,
                item["priority"],
                item["from"],
            )
            log_action(
                self.logs_path / "actions",
                {
                    "timestamp": now_iso(),
                    "correlation_id": cid,
                    "actor": "whatsapp_watcher",
                    "action_type": "message_detected",
                    "target": filename,
                    "result": "dry_run",
                    "parameters": {
                        "from": item["from"],
                        "priority": item["priority"],
                        "dry_run": True,
                        "dev_mode": self.dev_mode,
                    },
                },
            )
            return None

        self.needs_action.mkdir(parents=True, exist_ok=True)
        create_file_with_frontmatter(file_path, frontmatter, body)

        # Mark as processed
        self._processed_ids.add(item["message_id"])
        self._save_processed_ids()

        log_action(
            self.logs_path / "actions",
            {
                "timestamp": now_iso(),
                "correlation_id": cid,
                "actor": "whatsapp_watcher",
                "action_type": "message_processed",
                "target": filename,
                "result": "success",
                "parameters": {
                    "from": item["from"],
                    "priority": item["priority"],
                    "dry_run": False,
                    "dev_mode": self.dev_mode,
                },
            },
        )

        self.logger.info("Created action file: %s (priority: %s)", filename, item["priority"])
        return file_path

    # ── Cleanup ────────────────────────────────────────────────────

    async def cleanup(self) -> None:
        """Clean up browser resources."""
        if self.browser:
            await self._save_session()
            await self.browser.close()
            self.logger.info("Browser closed")


# ── CLI Entry Point ────────────────────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="WhatsApp Watcher - AI Employee Perception Layer (⚠️ Use at own risk)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check and exit",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the WhatsApp watcher."""
    load_dotenv()
    args = _parse_args(argv)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    vault_path = os.getenv("VAULT_PATH", "./vault")
    check_interval = int(os.getenv("WHATSAPP_CHECK_INTERVAL", "60"))
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"

    whatsapp_config = _load_whatsapp_config()

    watcher = WhatsAppWatcher(
        vault_path=vault_path,
        check_interval=check_interval,
        whatsapp_config=whatsapp_config,
        dry_run=dry_run,
        dev_mode=dev_mode,
    )

    if args.once:
        logger.info("Running single WhatsApp check...")

        async def single_check() -> None:
            items = await watcher.check_for_updates()
            for item in items:
                await watcher.create_action_file(item)
            logger.info("Check complete. Found %d messages.", len(items))
            await watcher.cleanup()

        asyncio.run(single_check())
        return

    logger.info("Starting WhatsApp watcher (interval: %ds, dry_run: %s)", check_interval, dry_run)
    logger.warning("⚠️  WhatsApp Web automation may violate ToS. Use at your own risk.")

    async def run_with_cleanup():
        try:
            await watcher.run()
        finally:
            await watcher.cleanup()

    asyncio.run(run_with_cleanup())


if __name__ == "__main__":
    main()
