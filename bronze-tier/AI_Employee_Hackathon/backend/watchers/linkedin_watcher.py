"""LinkedIn watcher - monitors content sources for business posts.

This is a PERCEPTION layer component. It observes local content sources
(Content Calendar, Business Updates, Announcements) and creates action files
for LinkedIn posting. It never posts to LinkedIn directly.

Usage:
    # Continuous polling
    uv run python backend/watchers/linkedin_watcher.py

    # Single check
    uv run python backend/watchers/linkedin_watcher.py --once
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from backend.utils.frontmatter import create_file_with_frontmatter, extract_frontmatter
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


def _load_linkedin_config(config_path: str = "config/linkedin_config.json") -> dict[str, Any]:
    """Load LinkedIn configuration from JSON file."""
    path = Path(config_path)
    if not path.exists():
        logger.warning("LinkedIn config not found at %s, using defaults", config_path)
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


class LinkedInWatcher(BaseWatcher):
    """Watches content sources for LinkedIn posts and creates vault action files."""

    def __init__(
        self,
        vault_path: str,
        check_interval: int = 600,
        linkedin_config: dict[str, Any] | None = None,
        dry_run: bool = True,
        dev_mode: bool = True,
    ):
        super().__init__(vault_path, check_interval)
        self.linkedin_config = linkedin_config or {}
        self.dry_run = dry_run
        self.dev_mode = dev_mode
        self.posted_hashes_path = self.logs_path / "posted_content_hashes.json"
        self._posted_hashes: set[str] = set()
        self._consecutive_errors = 0

    # ── Content Hash Management ────────────────────────────────────

    def _load_posted_hashes(self) -> None:
        """Load posted content hashes from disk."""
        if not self.posted_hashes_path.exists():
            self._posted_hashes = set()
            return

        try:
            data = json.loads(self.posted_hashes_path.read_text(encoding="utf-8"))
            self._posted_hashes = set(data.get("hashes", []))
        except (json.JSONDecodeError, KeyError):
            self.logger.warning("Corrupted posted_hashes.json, starting fresh")
            self._posted_hashes = set()

    def _save_posted_hashes(self) -> None:
        """Save posted content hashes to disk."""
        self.posted_hashes_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"hashes": list(self._posted_hashes), "updated_at": now_iso()}
        self.posted_hashes_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _content_hash(self, content: str) -> str:
        """Generate hash of content for duplicate detection."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _is_duplicate(self, content: str) -> bool:
        """Check if content has already been posted."""
        content_hash = self._content_hash(content)
        return content_hash in self._posted_hashes

    def _mark_as_posted(self, content: str) -> None:
        """Mark content as posted."""
        content_hash = self._content_hash(content)
        self._posted_hashes.add(content_hash)
        self._save_posted_hashes()

    # ── Content Source Scanning ────────────────────────────────────

    def _scan_content_calendar(self) -> list[dict[str, Any]]:
        """Scan Content_Calendar.md for scheduled posts.

        Returns:
            List of post dicts ready for action file creation.
        """
        calendar_path = self.vault_path / "Content_Calendar.md"
        if not calendar_path.exists():
            self.logger.debug("Content_Calendar.md not found")
            return []

        content = calendar_path.read_text(encoding="utf-8")
        posts = []

        # Parse markdown sections for scheduled posts
        # Format: ### YYYY-MM-DD HH:MM AM/PM
        pattern = r"###\s+(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}\s+(?:AM|PM))\s*\n\*\*Type:\*\*\s+(.+?)\n\*\*Status:\*\*\s+(.+?)\n\n(.+?)(?=\n###|\n\*\*Hashtags|\Z)"

        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            scheduled_time_str = match.group(1)
            post_type = match.group(2).strip()
            status = match.group(3).strip()
            post_content = match.group(4).strip()

            # Skip if not ready
            if status.lower() not in ["ready", "scheduled"]:
                continue

            # Parse scheduled time
            try:
                scheduled_dt = datetime.strptime(scheduled_time_str, "%Y-%m-%d %I:%M %p")
                scheduled_dt = scheduled_dt.replace(tzinfo=UTC)
            except ValueError:
                self.logger.warning("Invalid date format: %s", scheduled_time_str)
                continue

            # Check if it's time to post (within next hour)
            now = datetime.now(UTC)
            hours_until = (scheduled_dt - now).total_seconds() / 3600

            if not (0 <= hours_until <= 1):
                continue  # Not yet time

            # Check for duplicate
            if self._is_duplicate(post_content):
                self.logger.debug("Skipping duplicate post")
                continue

            # Extract hashtags and media
            hashtags = self._extract_hashtags(content, scheduled_time_str)
            media = self._extract_media(content, scheduled_time_str)

            posts.append(
                {
                    "content": post_content,
                    "post_type": post_type.lower().replace(" ", "_"),
                    "scheduled_date": scheduled_dt.isoformat(),
                    "hashtags": hashtags,
                    "media": media,
                    "source": "Content_Calendar.md",
                }
            )

        return posts

    def _scan_business_updates(self) -> list[dict[str, Any]]:
        """Scan Business_Updates/ folder for new drafts.

        Returns:
            List of post dicts ready for action file creation.
        """
        updates_path = self.vault_path / "Business_Updates"
        if not updates_path.exists():
            return []

        posts = []

        for file_path in updates_path.glob("*.md"):
            # Skip if already processed
            if self._is_duplicate(file_path.name):
                continue

            content = file_path.read_text(encoding="utf-8")

            # Check for exclude keywords
            if self._has_exclude_keywords(content):
                continue

            # Extract frontmatter if exists
            frontmatter, body = extract_frontmatter(content)

            post_content = body.strip() if body else content.strip()

            # Check for duplicate content
            if self._is_duplicate(post_content):
                continue

            posts.append(
                {
                    "content": post_content,
                    "post_type": "business_update",
                    "scheduled_date": now_iso(),
                    "hashtags": frontmatter.get("hashtags", []),
                    "media": frontmatter.get("media"),
                    "source": file_path.name,
                }
            )

        return posts

    def _scan_announcements(self) -> list[dict[str, Any]]:
        """Scan Announcements/ folder for company announcements.

        Returns:
            List of post dicts ready for action file creation.
        """
        announcements_path = self.vault_path / "Announcements"
        if not announcements_path.exists():
            return []

        posts = []

        for file_path in announcements_path.glob("*.md"):
            # Skip if already processed
            if self._is_duplicate(file_path.name):
                continue

            content = file_path.read_text(encoding="utf-8")

            # Check for exclude keywords
            if self._has_exclude_keywords(content):
                continue

            # Extract frontmatter if exists
            frontmatter, body = extract_frontmatter(content)

            post_content = body.strip() if body else content.strip()

            # Check for duplicate content
            if self._is_duplicate(post_content):
                continue

            posts.append(
                {
                    "content": post_content,
                    "post_type": "announcement",
                    "scheduled_date": now_iso(),
                    "hashtags": frontmatter.get("hashtags", []),
                    "media": frontmatter.get("media"),
                    "source": file_path.name,
                    "priority": "high",  # Announcements are high priority
                }
            )

        return posts

    # ── Content Parsing Helpers ────────────────────────────────────

    def _extract_hashtags(self, content: str, after_marker: str) -> list[str]:
        """Extract hashtags from content after a marker."""
        # Find section after marker
        marker_pos = content.find(after_marker)
        if marker_pos == -1:
            return []

        section = content[marker_pos : marker_pos + 500]

        # Look for **Hashtags:** line
        match = re.search(r"\*\*Hashtags:\*\*\s+(.+)", section)
        if not match:
            return []

        hashtags_str = match.group(1).strip()
        return [tag.strip() for tag in hashtags_str.split() if tag.startswith("#")]

    def _extract_media(self, content: str, after_marker: str) -> str | None:
        """Extract media path from content after a marker."""
        marker_pos = content.find(after_marker)
        if marker_pos == -1:
            return None

        section = content[marker_pos : marker_pos + 500]

        # Look for **Media:** line
        match = re.search(r"\*\*Media:\*\*\s+(.+)", section)
        if not match:
            return None

        return match.group(1).strip()

    def _has_exclude_keywords(self, content: str) -> bool:
        """Check if content has exclude keywords."""
        exclude_keywords = self.linkedin_config.get("exclude_keywords", [])
        content_lower = content.lower()
        return any(keyword.lower() in content_lower for keyword in exclude_keywords)

    # ── Rate Limiting ───────────────────────────────────────────────

    def _check_rate_limits(self) -> bool:
        """Check if rate limits allow posting.

        Returns:
            True if within limits, False if exceeded.
        """
        # TODO: Implement rate limit checking
        # For now, always allow (rate limits enforced by MCP server)
        return True

    # ── Main Check Method ───────────────────────────────────────────

    async def check_for_updates(self) -> list[dict[str, Any]]:
        """Poll content sources for new posts.

        Returns:
            List of post dicts that need action files created.
        """
        self._load_posted_hashes()

        try:
            posts = []

            # Scan all content sources
            posts.extend(self._scan_content_calendar())
            posts.extend(self._scan_business_updates())
            posts.extend(self._scan_announcements())

            self._consecutive_errors = 0
            return posts

        except Exception:
            self._consecutive_errors += 1
            self.logger.exception(
                "Error scanning content sources (consecutive errors: %d)",
                self._consecutive_errors,
            )
            return []

    # ── Action File Creation ────────────────────────────────────────

    async def create_action_file(self, item: dict[str, Any]) -> Path | None:
        """Create a markdown action file in Needs_Action for a LinkedIn post.

        Args:
            item: Parsed post dict from check_for_updates.

        Returns:
            Path to created file, or None if dry_run.
        """
        content_slug = _slugify(item["content"][:50])
        timestamp = format_filename_timestamp()
        filename = f"linkedin-{content_slug}-{timestamp}.md"
        file_path = self.needs_action / filename

        post_id = f"LINKEDIN_{short_id()}_{timestamp}"

        frontmatter: dict[str, Any] = {
            "type": "linkedin_post",
            "id": post_id,
            "source": "linkedin_watcher",
            "content_source": item["source"],
            "post_type": item["post_type"],
            "scheduled_date": item["scheduled_date"],
            "priority": item.get("priority", "medium"),
            "status": "pending",
            "requires_approval": True,
        }

        hashtags_str = " ".join(item.get("hashtags", []))
        media_str = item.get("media", "None")

        body = f"""
## Post Content

{item["content"]}

## Metadata

- **Post Type:** {item["post_type"]}
- **Scheduled:** {item["scheduled_date"]}
- **Hashtags:** {hashtags_str if hashtags_str else "None"}
- **Media:** {media_str}

## Suggested Actions

- [ ] Review post content
- [ ] Approve for posting
- [ ] Schedule or post immediately
- [ ] Add additional hashtags if needed
"""

        cid = correlation_id()

        if self.dry_run:
            self.logger.info(
                "[DRY RUN] Would create action file: %s (type: %s)",
                filename,
                item["post_type"],
            )
            log_action(
                self.logs_path / "actions",
                {
                    "timestamp": now_iso(),
                    "correlation_id": cid,
                    "actor": "linkedin_watcher",
                    "action_type": "post_detected",
                    "target": filename,
                    "result": "dry_run",
                    "parameters": {
                        "post_type": item["post_type"],
                        "source": item["source"],
                        "dry_run": True,
                        "dev_mode": self.dev_mode,
                    },
                },
            )
            return None

        self.needs_action.mkdir(parents=True, exist_ok=True)
        create_file_with_frontmatter(file_path, frontmatter, body)

        # Mark as posted to prevent duplicates
        self._mark_as_posted(item["content"])

        log_action(
            self.logs_path / "actions",
            {
                "timestamp": now_iso(),
                "correlation_id": cid,
                "actor": "linkedin_watcher",
                "action_type": "post_processed",
                "target": filename,
                "result": "success",
                "parameters": {
                    "post_type": item["post_type"],
                    "source": item["source"],
                    "dry_run": False,
                    "dev_mode": self.dev_mode,
                },
            },
        )

        self.logger.info("Created action file: %s (type: %s)", filename, item["post_type"])
        return file_path


# ── CLI Entry Point ─────────────────────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LinkedIn Watcher - AI Employee Perception Layer"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check and exit",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the LinkedIn watcher."""
    load_dotenv()
    args = _parse_args(argv)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    vault_path = os.getenv("VAULT_PATH", "./vault")
    check_interval = int(os.getenv("LINKEDIN_CHECK_INTERVAL", "600"))
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"

    linkedin_config = _load_linkedin_config()

    watcher = LinkedInWatcher(
        vault_path=vault_path,
        check_interval=check_interval,
        linkedin_config=linkedin_config,
        dry_run=dry_run,
        dev_mode=dev_mode,
    )

    if args.once:
        logger.info("Running single LinkedIn check...")

        async def single_check() -> None:
            items = await watcher.check_for_updates()
            for item in items:
                await watcher.create_action_file(item)
            logger.info("Check complete. Found %d posts ready.", len(items))

        asyncio.run(single_check())
        return

    logger.info("Starting LinkedIn watcher (interval: %ds, dry_run: %s)", check_interval, dry_run)
    asyncio.run(watcher.run())


if __name__ == "__main__":
    main()
