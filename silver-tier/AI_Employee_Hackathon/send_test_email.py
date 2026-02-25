#!/usr/bin/env python3
"""Test script to send email via Email MCP server."""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.mcp_servers.gmail_client import GmailClient
from backend.mcp_servers.rate_limiter import RateLimiter
from backend.mcp_servers.approval import find_approval, consume_approval
from backend.utils.logging_utils import log_action
from backend.utils.timestamps import now_iso
from backend.utils.uuid_utils import correlation_id

# Load .env from config directory
env_path = Path(__file__).parent / "config" / ".env"
print(f"Loading .env from: {env_path}")
print(f".env exists: {env_path.exists()}")
load_dotenv(env_path)

DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
print(f"DEV_MODE env var: {os.getenv('DEV_MODE')}")
VAULT_PATH = os.getenv("VAULT_PATH", "./vault")
CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "config/credentials.json")
TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "config/token.json")


async def send_email_direct(to: str, subject: str, body: str) -> str:
    """Send email directly using Gmail client."""
    print(f"DEV_MODE: {DEV_MODE}")
    print(f"Vault path: {VAULT_PATH}")
    print(f"To: {to}")
    print(f"Subject: {subject}")
    print()

    # Check for approval
    approval = find_approval(VAULT_PATH, "email_send", to=to)
    if approval is None:
        return f"ERROR: No approval file found for sending to {to}"

    print(f"[OK] Found approval file: {approval['path']}")

    # DEV_MODE check
    if DEV_MODE:
        print("[DEV_MODE] Email would be sent but DEV_MODE is enabled")
        return f"[DEV_MODE] Send logged but not executed. To: {to}, Subject: {subject}"

    # Initialize Gmail client
    print("Initializing Gmail client...")
    gmail = GmailClient(
        credentials_path=CREDENTIALS_PATH,
        token_path=TOKEN_PATH,
    )
    gmail.authenticate()
    print("[OK] Gmail authenticated")

    # Check rate limit
    rate_limiter = RateLimiter()
    allowed, wait_seconds = rate_limiter.check()
    if not allowed:
        return f"ERROR: Rate limit exceeded. Wait {wait_seconds} seconds."
    print("[OK] Rate limit OK")

    # Send email
    print(f"Sending email to {to}...")
    result = gmail.send_message(to, subject, body)

    # Record send and consume approval
    rate_limiter.record_send()
    consume_approval(approval["path"], VAULT_PATH)

    print(f"[OK] Email sent successfully!")
    print(f"  Message ID: {result['message_id']}")
    print(f"  Thread ID: {result['thread_id']}")

    # Log action
    log_dir = Path(VAULT_PATH) / "Logs" / "actions"
    log_action(
        log_dir,
        {
            "timestamp": now_iso(),
            "correlation_id": correlation_id(),
            "actor": "send_test_email_script",
            "action_type": "send_email",
            "target": to,
            "result": "success",
            "parameters": {
                "subject": subject[:50],
                "message_id": result["message_id"],
            },
        },
    )

    return f"Email sent successfully. Message ID: {result['message_id']}"


async def main():
    """Main entry point."""
    to = "zartashakhan775@gmail.com"
    subject = "Hello from my AI Employee!"
    body = "Hi Zartasha! This email was sent by my Personal AI Employee. Pretty cool right?"

    result = await send_email_direct(to, subject, body)
    print()
    print("=" * 60)
    print("RESULT:", result)
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
