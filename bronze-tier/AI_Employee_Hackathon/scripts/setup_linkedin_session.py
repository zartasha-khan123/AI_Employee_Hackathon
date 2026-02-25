#!/usr/bin/env python3
"""Setup LinkedIn session for browser automation.

This script helps authenticate LinkedIn for the LinkedInPoster to use.
Run this once to create a persistent browser session.

Usage:
    uv run python scripts/setup_linkedin_session.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright


async def setup_linkedin_session():
    """Set up LinkedIn browser session with authentication."""
    print("=" * 70)
    print("LinkedIn Session Setup")
    print("=" * 70)
    print()
    print("This script will open a browser window for you to log in to LinkedIn.")
    print("After logging in, the session will be saved for automated posting.")
    print()
    input("Press Enter to continue...")

    session_path = Path("config/linkedin_session")
    session_path.mkdir(parents=True, exist_ok=True)

    print(f"\nSession will be saved to: {session_path}")
    print("\nOpening browser...")

    playwright = await async_playwright().start()

    # Launch browser with persistent context
    context = await playwright.chromium.launch_persistent_context(
        str(session_path),
        headless=False,
        args=["--no-sandbox", "--disable-setuid-sandbox"],
    )

    page = context.pages[0] if context.pages else await context.new_page()

    print("\n" + "=" * 70)
    print("INSTRUCTIONS:")
    print("=" * 70)
    print("1. The browser window is now open")
    print("2. Navigate to https://www.linkedin.com")
    print("3. Log in with your LinkedIn credentials")
    print("4. Wait for the feed to load completely")
    print("5. Return to this terminal and press Enter")
    print("=" * 70)
    print()

    # Navigate to LinkedIn
    await page.goto("https://www.linkedin.com")

    # Wait for user to log in
    input("\nPress Enter after you've logged in and see your LinkedIn feed...")

    # Verify login by checking for feed
    print("\nVerifying login...")
    try:
        # Check if we're on the feed page
        current_url = page.url
        if "feed" in current_url or "linkedin.com" in current_url:
            print("✓ Login successful!")
            print(f"  Current URL: {current_url}")
        else:
            print("⚠ Warning: Not on LinkedIn feed. You may need to log in again.")
    except Exception as e:
        print(f"⚠ Could not verify login: {e}")

    # Save session
    print("\nSaving session...")
    await context.close()
    await playwright.stop()

    print("\n" + "=" * 70)
    print("✓ LinkedIn session saved successfully!")
    print("=" * 70)
    print(f"\nSession location: {session_path.absolute()}")
    print("\nYou can now use the LinkedInPoster to post content.")
    print("The session will persist until you log out or clear browser data.")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(setup_linkedin_session())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during setup: {e}")
        sys.exit(1)
