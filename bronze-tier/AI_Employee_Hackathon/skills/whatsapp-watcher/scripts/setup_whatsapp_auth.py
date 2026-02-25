#!/usr/bin/env python3
"""Setup WhatsApp Web authentication.

This script launches a browser, navigates to WhatsApp Web, and waits for
you to scan the QR code with your phone. The session is then saved for
future use by the WhatsApp watcher.

Usage:
    uv run python skills/whatsapp-watcher/scripts/setup_whatsapp_auth.py
"""

import asyncio
import sys
from pathlib import Path


async def main() -> None:
    """Run WhatsApp Web authentication setup."""
    print("=" * 60)
    print("WhatsApp Web Authentication Setup")
    print("=" * 60)
    print()
    print("⚠️  WARNING: WhatsApp Web automation may violate WhatsApp ToS")
    print("   Use at your own risk. Your account may be banned.")
    print()
    print("Press Ctrl+C to cancel, or Enter to continue...")
    input()

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Error: Playwright not installed")
        print("\nInstall with:")
        print("  uv add playwright")
        print("  uv run playwright install chromium")
        sys.exit(1)

    session_path = Path("config/whatsapp_session")
    session_path.mkdir(parents=True, exist_ok=True)

    print("\n🌐 Launching browser...")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,  # Show browser for QR code scan
        args=["--no-sandbox", "--disable-setuid-sandbox"],
    )

    context = await browser.new_context()
    page = await context.new_page()

    print("📱 Navigating to WhatsApp Web...")
    await page.goto("https://web.whatsapp.com")

    print("\n" + "=" * 60)
    print("SCAN QR CODE WITH YOUR PHONE")
    print("=" * 60)
    print()
    print("1. Open WhatsApp on your phone")
    print("2. Tap Menu (⋮) or Settings")
    print("3. Tap 'Linked Devices'")
    print("4. Tap 'Link a Device'")
    print("5. Scan the QR code in the browser")
    print()
    print("Waiting for authentication...")

    try:
        # Wait for chat list to appear (indicates successful auth)
        await page.wait_for_selector(
            'div[data-testid="chat-list"]',
            timeout=120000,  # 2 minutes
        )

        print("\n✅ Authentication successful!")

        # Save session
        print("💾 Saving session...")
        await context.storage_state(path=str(session_path / "state.json"))

        print(f"✅ Session saved to {session_path}")
        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print()
        print("You can now run the WhatsApp watcher:")
        print("  uv run python backend/watchers/whatsapp_watcher.py --once")
        print()
        print("Remember to set DEV_MODE=false in .env to enable real monitoring")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nAuthentication failed or timed out.")
        print("Please try again.")
        sys.exit(1)

    finally:
        await browser.close()
        await playwright.stop()


if __name__ == "__main__":
    asyncio.run(main())
