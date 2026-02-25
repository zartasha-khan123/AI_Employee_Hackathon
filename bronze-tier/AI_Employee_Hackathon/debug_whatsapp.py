#!/usr/bin/env python3
"""Debug script to check WhatsApp Web page state."""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def main():
    print("Starting WhatsApp Web debug...")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,
        args=["--no-sandbox", "--disable-setuid-sandbox"],
    )

    context = await browser.new_context()
    page = await context.new_page()

    print("Navigating to WhatsApp Web...")
    await page.goto("https://web.whatsapp.com")

    print("Waiting 5 seconds for page to load...")
    await asyncio.sleep(5)

    # Take screenshot
    screenshot_path = Path("whatsapp_debug.png")
    await page.screenshot(path=str(screenshot_path))
    print(f"Screenshot saved: {screenshot_path}")

    # Get page title
    title = await page.title()
    print(f"Page title: {title}")

    # Get page URL
    url = page.url
    print(f"Current URL: {url}")

    # Check for various selectors
    selectors_to_check = [
        'canvas[aria-label="Scan me!"]',
        'div[data-testid="chat-list"]',
        'div[data-testid="intro-md-beta-logo-dark"]',
        'div[data-testid="intro-md-beta-logo-light"]',
        'div._2Ts6i',  # Old QR code container
        'div[role="button"]',
    ]

    print("\nChecking selectors:")
    for selector in selectors_to_check:
        try:
            element = await page.query_selector(selector)
            if element:
                print(f"  FOUND: {selector}")
            else:
                print(f"  NOT FOUND: {selector}")
        except Exception as e:
            print(f"  ERROR checking {selector}: {e}")

    # Get page content snippet
    print("\nPage content (first 500 chars):")
    content = await page.content()
    print(content[:500])

    print("\nWaiting 30 seconds for manual inspection...")
    await asyncio.sleep(30)

    await browser.close()
    print("Debug complete")


if __name__ == "__main__":
    asyncio.run(main())
