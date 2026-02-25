"""Google Calendar watcher - monitors upcoming events and creates vault action files.

This is a PERCEPTION layer component. It observes Google Calendar and writes action files
to the vault for events requiring preparation. It never modifies or deletes calendar events.

Usage:
    # Continuous polling
    uv run python backend/watchers/calendar_watcher.py

    # Single check
    uv run python backend/watchers/calendar_watcher.py --once

    # Auth only (first-time setup)
    uv run python backend/watchers/calendar_watcher.py --auth-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.utils.frontmatter import create_file_with_frontmatter
from backend.utils.logging_utils import log_action
from backend.utils.timestamps import format_filename_timestamp, now_iso
from backend.utils.uuid_utils import correlation_id, short_id
from backend.watchers.base_watcher import BaseWatcher

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

MAX_BACKOFF_SECONDS = 60.0
MAX_RETRIES = 3


def _slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a filename-safe slug."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:max_length].rstrip("-")


def _load_calendar_config(config_path: str = "config/calendar_config.json") -> dict[str, Any]:
    """Load Calendar configuration from JSON file."""
    path = Path(config_path)
    if not path.exists():
        logger.warning("Calendar config not found at %s, using defaults", config_path)
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


class CalendarWatcher(BaseWatcher):
    """Watches Google Calendar for upcoming events and creates vault action files."""

    def __init__(
        self,
        vault_path: str,
        credentials_path: str = "config/credentials.json",
        token_path: str = "config/calendar_token.json",
        check_interval: int = 300,
        calendar_config: dict[str, Any] | None = None,
        dry_run: bool = True,
        dev_mode: bool = True,
    ):
        super().__init__(vault_path, check_interval)
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.calendar_config = calendar_config or {}
        self.dry_run = dry_run
        self.dev_mode = dev_mode
        self.service: Any = None
        self.processed_ids_path = self.logs_path / "processed_events.json"
        self._processed_ids: dict[str, str] = {}
        self._last_cleanup: str | None = None
        self._consecutive_errors = 0
        self._backoff_delay = 1.0

    # ── Authentication ──────────────────────────────────────────────

    def _authenticate(self) -> None:
        """Load or refresh OAuth credentials and build the Calendar API service.

        Raises:
            FileNotFoundError: If token file doesn't exist and can't authenticate.
            RuntimeError: If authentication fails after token refresh.
        """
        creds: Credentials | None = None

        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if creds and creds.expired and creds.refresh_token:
            self.logger.info("Refreshing expired Calendar token")
            creds.refresh(Request())
            self.token_path.write_text(creds.to_json(), encoding="utf-8")

        if not creds or not creds.valid:
            msg = (
                f"No valid Calendar token at {self.token_path}. "
                "Run: uv run python skills/calendar-watcher/scripts/setup_calendar_oauth.py"
            )
            raise FileNotFoundError(msg)

        self.service = build("calendar", "v3", credentials=creds)
        self.logger.info("Calendar API authenticated successfully")

    # ── Processed IDs ───────────────────────────────────────────────

    def _load_processed_ids(self) -> None:
        """Load processed event IDs from disk."""
        if not self.processed_ids_path.exists():
            self._processed_ids = {}
            self._last_cleanup = None
            return

        try:
            data = json.loads(self.processed_ids_path.read_text(encoding="utf-8"))
            self._processed_ids = data.get("processed_ids", {})
            self._last_cleanup = data.get("last_cleanup")
        except (json.JSONDecodeError, KeyError):
            self.logger.warning("Corrupted processed_events.json, starting fresh")
            self._processed_ids = {}
            self._last_cleanup = None

    def _save_processed_ids(self) -> None:
        """Save processed event IDs to disk."""
        self.processed_ids_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "processed_ids": self._processed_ids,
            "last_cleanup": self._last_cleanup or now_iso(),
        }
        self.processed_ids_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _cleanup_old_ids(self) -> None:
        """Remove processed IDs older than retention period."""
        retention_days = self.calendar_config.get("processed_ids_retention_days", 7)
        now = now_iso()

        # Only clean up once per day
        if self._last_cleanup:
            from backend.utils.timestamps import is_within_hours

            if is_within_hours(self._last_cleanup, 24):
                return

        cutoff_ids = []
        for event_id, processed_at in self._processed_ids.items():
            try:
                from backend.utils.timestamps import is_within_hours

                if not is_within_hours(processed_at, retention_days * 24):
                    cutoff_ids.append(event_id)
            except (ValueError, TypeError):
                cutoff_ids.append(event_id)

        for event_id in cutoff_ids:
            del self._processed_ids[event_id]

        self._last_cleanup = now
        if cutoff_ids:
            self.logger.info("Cleaned up %d old processed event IDs", len(cutoff_ids))

    # ── Event Fetching ──────────────────────────────────────────────

    def _fetch_events(self) -> list[dict[str, Any]]:
        """Fetch upcoming events from Calendar API (synchronous).

        Returns:
            List of parsed event dicts ready for action file creation.
        """
        if self.service is None:
            self._authenticate()

        lookahead_hours = self.calendar_config.get("lookahead_hours", 48)
        exclude_event_types = self.calendar_config.get("exclude_event_types", [])
        vip_domains = self.calendar_config.get("vip_domains", [])

        # Calculate time range
        now = datetime.now(UTC)
        time_min = now.isoformat()
        time_max = (now + timedelta(hours=lookahead_hours)).isoformat()

        # Fetch events
        events_result = (
            self.service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])
        if not events:
            self.logger.debug("No upcoming events found")
            return []

        parsed: list[dict[str, Any]] = []

        for event in events:
            event_id = event["id"]

            # Skip if already processed
            if event_id in self._processed_ids:
                continue

            summary = event.get("summary", "No Title")
            description = event.get("description", "")
            start = event.get("start", {})
            end = event.get("end", {})

            # Get start time (handle all-day events)
            start_time = start.get("dateTime", start.get("date", ""))
            end_time = end.get("dateTime", end.get("date", ""))

            # Skip excluded event types
            if self._is_excluded_event(summary, description, exclude_event_types):
                self.logger.debug("Skipping excluded event type: %s", summary)
                continue

            # Get attendees
            attendees = event.get("attendees", [])
            attendee_emails = [a.get("email", "") for a in attendees]

            # Check if requires preparation
            requires_prep = self._requires_preparation(
                summary, description, attendee_emails, start_time
            )

            # Skip if no preparation needed
            if not requires_prep:
                continue

            # Classify priority
            priority = self._classify_priority(
                summary, description, attendee_emails, start_time, vip_domains
            )

            parsed.append(
                {
                    "event_id": event_id,
                    "summary": summary,
                    "description": description,
                    "start_time": start_time,
                    "end_time": end_time,
                    "attendees": attendee_emails,
                    "priority": priority,
                    "requires_preparation": requires_prep,
                    "location": event.get("location", ""),
                    "html_link": event.get("htmlLink", ""),
                }
            )

        return parsed

    async def check_for_updates(self) -> list[dict[str, Any]]:
        """Poll Calendar for upcoming events requiring preparation.

        Returns:
            List of event dicts that need action files created.
        """
        self._load_processed_ids()
        self._cleanup_old_ids()

        try:
            items = await asyncio.to_thread(self._fetch_events_with_retry)
            self._consecutive_errors = 0
            self._backoff_delay = 1.0
            return items
        except FileNotFoundError:
            raise
        except Exception:
            self._consecutive_errors += 1
            self.logger.exception(
                "Error fetching Calendar events (consecutive errors: %d)",
                self._consecutive_errors,
            )
            self._log_error("calendar_api", "fetch_failed")
            return []

    def _fetch_events_with_retry(self) -> list[dict[str, Any]]:
        """Fetch events with retry logic for transient errors."""
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                return self._fetch_events()
            except HttpError as e:
                last_error = e
                status = e.resp.status if hasattr(e, "resp") else 0

                if status == 401:
                    self.logger.warning("Auth error, refreshing token")
                    self.service = None
                    self._authenticate()
                    continue

                if status == 429:
                    delay = min(self._backoff_delay * (2**attempt), MAX_BACKOFF_SECONDS)
                    self.logger.warning("Rate limited, backing off %.1fs", delay)
                    import time

                    time.sleep(delay)
                    continue

                if status == 403:
                    self.logger.error("Permission denied: %s", e)
                    raise

                self.logger.warning("Calendar API error (attempt %d): %s", attempt + 1, e)
                import time

                time.sleep(self._backoff_delay * (2**attempt))

            except (ConnectionError, TimeoutError) as e:
                last_error = e
                self.logger.warning("Network error (attempt %d): %s", attempt + 1, e)
                import time

                time.sleep(self._backoff_delay * (2**attempt))

        if last_error:
            raise last_error
        return []

    # ── Event Classification ────────────────────────────────────────

    def _requires_preparation(
        self, summary: str, description: str, attendees: list[str], start_time: str
    ) -> bool:
        """Determine if an event requires preparation."""
        text = f"{summary} {description}".lower()

        # Check for preparation keywords
        prep_keywords = ["prepare", "review", "present", "demo", "pitch", "proposal"]
        if any(kw in text for kw in prep_keywords):
            return True

        # External attendees (not same domain as user)
        if attendees and len(attendees) > 1:
            return True

        # Events within preparation threshold
        preparation_threshold_hours = self.calendar_config.get("preparation_threshold_hours", 2)
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            now = datetime.now(UTC)
            hours_until = (start_dt - now).total_seconds() / 3600

            if 0 < hours_until <= preparation_threshold_hours:
                return True
        except (ValueError, TypeError):
            pass

        return False

    def _classify_priority(
        self,
        summary: str,
        description: str,
        attendees: list[str],
        start_time: str,
        vip_domains: list[str],
    ) -> str:
        """Classify event priority based on keywords, attendees, and timing."""
        text = f"{summary} {description}".lower()
        priority_keywords = self.calendar_config.get("priority_keywords", {})

        # Check for high priority keywords
        for kw in priority_keywords.get("high", []):
            if kw in text:
                return "high"

        # Check for VIP attendees
        for email in attendees:
            for domain in vip_domains:
                if domain.lower() in email.lower():
                    return "high"

        # Check time proximity (< 2 hours = high priority)
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            now = datetime.now(UTC)
            hours_until = (start_dt - now).total_seconds() / 3600

            if 0 < hours_until <= 2:
                return "high"
        except (ValueError, TypeError):
            pass

        # Check for medium priority keywords
        for kw in priority_keywords.get("medium", []):
            if kw in text:
                return "medium"

        return "low"

    @staticmethod
    def _is_excluded_event(summary: str, description: str, exclude_patterns: list[str]) -> bool:
        """Check if an event matches any exclusion pattern."""
        text = f"{summary} {description}".lower()
        return any(pattern.lower() in text for pattern in exclude_patterns)

    # ── Action File Creation ────────────────────────────────────────

    async def create_action_file(self, item: dict[str, Any]) -> Path | None:
        """Create a markdown action file in Needs_Action for an upcoming event.

        Args:
            item: Parsed event dict from check_for_updates.

        Returns:
            Path to created file, or None if dry_run.
        """
        summary_slug = _slugify(item.get("summary", "no-title"))
        timestamp = format_filename_timestamp()
        filename = f"calendar-{summary_slug}-{timestamp}.md"
        file_path = self.needs_action / filename

        event_id = f"EVENT_{short_id()}_{timestamp}"

        frontmatter: dict[str, Any] = {
            "type": "calendar_event",
            "id": event_id,
            "source": "calendar_watcher",
            "event_id": item["event_id"],
            "summary": item["summary"],
            "start_time": item["start_time"],
            "end_time": item["end_time"],
            "attendees": item["attendees"],
            "priority": item["priority"],
            "status": "pending",
            "requires_preparation": item["requires_preparation"],
        }

        attendees_str = "\n".join([f"- {email}" for email in item.get("attendees", [])])
        location_str = item.get("location", "No location specified")

        body = f"""
## Event Details

**Summary:** {item["summary"]}

**Start:** {item["start_time"]}
**End:** {item["end_time"]}
**Location:** {location_str}

**Attendees:**
{attendees_str if attendees_str else "- No attendees listed"}

## Description

{item.get("description", "No description provided")}

## Preparation Tasks

- [ ] Review meeting agenda
- [ ] Prepare materials or presentation
- [ ] Check attendee backgrounds
- [ ] Set up meeting space/tech

## Links

- [View in Calendar]({item.get("html_link", "#")})
"""

        cid = correlation_id()

        if self.dry_run:
            self.logger.info(
                "[DRY RUN] Would create action file: %s (priority: %s, event: %s)",
                filename,
                item["priority"],
                item["summary"],
            )
            log_action(
                self.logs_path / "actions",
                {
                    "timestamp": now_iso(),
                    "correlation_id": cid,
                    "actor": "calendar_watcher",
                    "action_type": "event_detected",
                    "target": filename,
                    "result": "dry_run",
                    "parameters": {
                        "event_id": item["event_id"],
                        "summary": item["summary"],
                        "priority": item["priority"],
                        "dry_run": True,
                        "dev_mode": self.dev_mode,
                    },
                },
            )
            return None

        self.needs_action.mkdir(parents=True, exist_ok=True)
        create_file_with_frontmatter(file_path, frontmatter, body)

        # Track as processed
        self._processed_ids[item["event_id"]] = now_iso()
        self._save_processed_ids()

        log_action(
            self.logs_path / "actions",
            {
                "timestamp": now_iso(),
                "correlation_id": cid,
                "actor": "calendar_watcher",
                "action_type": "event_processed",
                "target": filename,
                "result": "success",
                "parameters": {
                    "event_id": item["event_id"],
                    "summary": item["summary"],
                    "priority": item["priority"],
                    "dry_run": False,
                    "dev_mode": self.dev_mode,
                },
            },
        )

        self.logger.info("Created action file: %s (priority: %s)", filename, item["priority"])
        return file_path

    # ── Error Logging ───────────────────────────────────────────────

    def _log_error(self, target: str, error_msg: str) -> None:
        """Log an error to the vault error logs."""
        try:
            log_action(
                self.logs_path / "errors",
                {
                    "timestamp": now_iso(),
                    "correlation_id": correlation_id(),
                    "actor": "calendar_watcher",
                    "action_type": "error",
                    "target": target,
                    "error": error_msg,
                    "details": {
                        "consecutive_errors": self._consecutive_errors,
                        "dev_mode": self.dev_mode,
                    },
                    "result": "failure",
                },
            )
        except Exception:
            self.logger.exception("Failed to write error log")


# ── CLI Entry Point ─────────────────────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calendar Watcher - AI Employee Perception Layer")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check and exit",
    )
    parser.add_argument(
        "--auth-only",
        action="store_true",
        help="Only authenticate and save token, then exit",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the Calendar watcher."""
    load_dotenv()
    args = _parse_args(argv)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    vault_path = os.getenv("VAULT_PATH", "./vault")
    credentials_path = os.getenv("CALENDAR_CREDENTIALS_PATH", "config/credentials.json")
    token_path = os.getenv("CALENDAR_TOKEN_PATH", "config/calendar_token.json")
    check_interval = int(os.getenv("CALENDAR_CHECK_INTERVAL", "300"))
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"

    calendar_config = _load_calendar_config()

    watcher = CalendarWatcher(
        vault_path=vault_path,
        credentials_path=credentials_path,
        token_path=token_path,
        check_interval=check_interval,
        calendar_config=calendar_config,
        dry_run=dry_run,
        dev_mode=dev_mode,
    )

    if args.auth_only:
        logger.info("Authenticating Calendar API...")
        watcher._authenticate()
        logger.info("Authentication successful. Token saved to %s", token_path)
        return

    if args.once:
        logger.info("Running single Calendar check...")

        async def single_check() -> None:
            items = await watcher.check_for_updates()
            for item in items:
                await watcher.create_action_file(item)
            logger.info("Check complete. Found %d events requiring preparation.", len(items))

        asyncio.run(single_check())
        return

    logger.info("Starting Calendar watcher (interval: %ds, dry_run: %s)", check_interval, dry_run)
    asyncio.run(watcher.run())


if __name__ == "__main__":
    main()
