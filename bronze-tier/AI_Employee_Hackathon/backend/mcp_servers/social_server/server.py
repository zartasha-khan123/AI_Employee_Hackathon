"""Social Media MCP Server - LinkedIn and Twitter posting with safety controls."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from backend.mcp_servers.social_server.linkedin_poster import LinkedInPoster
from backend.mcp_servers.social_server.safety import SocialSafetyChecker
from backend.utils.logging_utils import log_action
from backend.utils.timestamps import now_iso
from backend.utils.uuid_utils import correlation_id

# Configuration
load_dotenv()

DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
VAULT_PATH = os.getenv("VAULT_PATH", "./vault")
LINKEDIN_SESSION_PATH = os.getenv("LINKEDIN_SESSION_PATH", "config/linkedin_session")

# Logging to stderr (stdout reserved for MCP JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


# MCP Server
mcp = FastMCP(
    "social-mcp-server",
    instructions=(
        "Social media tools for LinkedIn and Twitter. "
        "All posts require approval file in vault/Approved/. "
        "Rate limited to 5 posts per platform per day."
    ),
)


@mcp.tool()
async def post_linkedin(content: str, image_path: str | None = None) -> str:
    """Post content to LinkedIn.

    ALWAYS requires human approval via vault/Approved/ file.
    Rate limited to 5 posts per day.

    Args:
        content: Post text content (max 3000 characters).
        image_path: Optional path to image file to attach.

    Returns:
        Success message with post URL or error message.
    """
    cid = correlation_id()

    # Validate content length
    if len(content) > 3000:
        return "Error: LinkedIn posts are limited to 3000 characters"

    # DEV_MODE check
    if DEV_MODE:
        _log_action("post_linkedin", "simulated", cid, {"content_length": len(content)})
        return (
            f"[DEV_MODE] LinkedIn post simulated. "
            f"Content length: {len(content)} chars. "
            f"Image: {'Yes' if image_path else 'No'}"
        )

    # Check for approval
    approval = _find_approval("linkedin_post", content=content)
    if not approval:
        return (
            "Rejected: No matching approval file found in vault/Approved/ "
            "for LinkedIn post. Create approval file with type: linkedin_post"
        )

    # Check rate limit
    if not _check_rate_limit("linkedin"):
        return "Rejected: Rate limit exceeded (5 posts/day for LinkedIn)"

    # Post to LinkedIn
    try:
        poster = LinkedInPoster(session_path=LINKEDIN_SESSION_PATH)
        post_url = await poster.post(content, image_path)

        # Record post and consume approval
        _record_post("linkedin")
        _consume_approval(approval["path"])

        _log_action("post_linkedin", "success", cid, {"post_url": post_url})
        return f"LinkedIn post published successfully. URL: {post_url}"

    except Exception as e:
        logger.exception("Failed to post to LinkedIn")
        _log_action("post_linkedin", "error", cid, {"error": str(e)})
        return f"Error posting to LinkedIn: {e}"


@mcp.tool()
async def post_twitter(content: str, image_path: str | None = None) -> str:
    """Post content to Twitter/X.

    ALWAYS requires human approval via vault/Approved/ file.
    Rate limited to 5 posts per day.

    Args:
        content: Tweet text (max 280 characters).
        image_path: Optional path to image file to attach.

    Returns:
        Success message with tweet URL or error message.
    """
    cid = correlation_id()

    # Validate content length
    if len(content) > 280:
        return "Error: Tweets are limited to 280 characters"

    # DEV_MODE check
    if DEV_MODE:
        _log_action("post_twitter", "simulated", cid, {"content_length": len(content)})
        return (
            f"[DEV_MODE] Twitter post simulated. "
            f"Content length: {len(content)} chars. "
            f"Image: {'Yes' if image_path else 'No'}"
        )

    # Check for approval
    approval = _find_approval("twitter_post", content=content)
    if not approval:
        return (
            "Rejected: No matching approval file found in vault/Approved/ "
            "for Twitter post. Create approval file with type: twitter_post"
        )

    # Check rate limit
    if not _check_rate_limit("twitter"):
        return "Rejected: Rate limit exceeded (5 posts/day for Twitter)"

    # Post to Twitter (placeholder - implementation needed)
    _log_action("post_twitter", "not_implemented", cid)
    return "Error: Twitter posting not yet implemented (Platinum tier feature)"


def _find_approval(post_type: str, content: str) -> dict[str, Any] | None:
    """Find matching approval file in vault/Approved/."""
    approved_dir = Path(VAULT_PATH) / "Approved"
    if not approved_dir.exists():
        return None

    for file_path in approved_dir.glob("*.md"):
        try:
            from backend.utils.frontmatter import extract_frontmatter

            file_content = file_path.read_text(encoding="utf-8")
            frontmatter, body = extract_frontmatter(file_content)

            if frontmatter.get("type") == post_type:
                # Check if content matches (first 100 chars)
                if content[:100] in body:
                    return {"path": str(file_path), "type": post_type}
        except Exception:
            continue

    return None


def _check_rate_limit(platform: str) -> bool:
    """Check if rate limit allows posting."""
    # Simple file-based rate limiting
    rate_limit_file = Path(VAULT_PATH) / "Logs" / "rate_limits" / f"{platform}_posts.txt"
    rate_limit_file.parent.mkdir(parents=True, exist_ok=True)

    if not rate_limit_file.exists():
        return True

    # Read today's post count
    from datetime import datetime, UTC

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    content = rate_limit_file.read_text(encoding="utf-8")
    today_posts = content.count(today)

    return today_posts < 5  # Max 5 posts per day


def _record_post(platform: str) -> None:
    """Record post for rate limiting."""
    rate_limit_file = Path(VAULT_PATH) / "Logs" / "rate_limits" / f"{platform}_posts.txt"
    rate_limit_file.parent.mkdir(parents=True, exist_ok=True)

    with rate_limit_file.open("a", encoding="utf-8") as f:
        f.write(f"{now_iso()}\n")


def _consume_approval(approval_path: str) -> None:
    """Move approval file to Done/ after execution."""
    from shutil import move

    approval_file = Path(approval_path)
    done_dir = Path(VAULT_PATH) / "Done"
    done_dir.mkdir(exist_ok=True)

    # Update frontmatter
    from backend.utils.frontmatter import update_frontmatter

    update_frontmatter(approval_file, {"status": "done", "completed_at": now_iso()})

    # Move to Done
    dest = done_dir / approval_file.name
    move(str(approval_file), str(dest))


def _log_action(action_type: str, result: str, cid: str, params: dict[str, Any] | None = None) -> None:
    """Log action to vault/Logs/actions/."""
    log_dir = Path(VAULT_PATH) / "Logs" / "actions"
    try:
        log_action(
            log_dir,
            {
                "timestamp": now_iso(),
                "correlation_id": cid,
                "actor": "social_mcp",
                "action_type": action_type,
                "target": "social_media",
                "result": result,
                "parameters": params or {},
            },
        )
    except OSError:
        logger.exception("Failed to write audit log")


def main() -> None:
    """CLI entry point for the social MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
