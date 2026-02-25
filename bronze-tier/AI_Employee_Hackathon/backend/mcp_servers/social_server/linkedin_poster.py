"""LinkedIn poster using browser automation."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


class LinkedInPoster:
    """Posts content to LinkedIn using browser automation."""

    def __init__(self, session_path: str | Path):
        """Initialize LinkedIn poster.

        Args:
            session_path: Path to browser session storage.
        """
        self.session_path = Path(session_path)
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def post(self, content: str, image_path: str | None = None) -> str:
        """Post content to LinkedIn.

        Args:
            content: Post text content.
            image_path: Optional path to image file.

        Returns:
            URL of the published post.

        Raises:
            Exception: If posting fails.
        """
        try:
            await self._init_browser()
            await self._navigate_to_linkedin()
            await self._create_post(content, image_path)
            post_url = await self._get_post_url()
            return post_url
        finally:
            await self._cleanup()

    async def _init_browser(self) -> None:
        """Initialize browser with session."""
        playwright = await async_playwright().start()

        # Check if session exists
        state_file = self.session_path / "state.json"

        if state_file.exists():
            # Load existing session
            context = await playwright.chromium.launch_persistent_context(
                str(self.session_path),
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            self.page = context.pages[0] if context.pages else await context.new_page()
        else:
            # New session - user needs to authenticate
            raise Exception(
                "LinkedIn session not found. Please authenticate first using "
                "the LinkedIn watcher setup script."
            )

    async def _navigate_to_linkedin(self) -> None:
        """Navigate to LinkedIn feed."""
        if not self.page:
            raise Exception("Browser not initialized")

        await self.page.goto("https://www.linkedin.com/feed/")
        await asyncio.sleep(2)  # Wait for page load

    async def _create_post(self, content: str, image_path: str | None = None) -> None:
        """Create and publish LinkedIn post.

        Args:
            content: Post text content.
            image_path: Optional path to image file.
        """
        if not self.page:
            raise Exception("Browser not initialized")

        # Click "Start a post" button
        start_post_selector = 'button[aria-label*="Start a post"]'
        await self.page.wait_for_selector(start_post_selector, timeout=10000)
        await self.page.click(start_post_selector)
        await asyncio.sleep(1)

        # Type content in the post editor
        editor_selector = 'div[role="textbox"][contenteditable="true"]'
        await self.page.wait_for_selector(editor_selector, timeout=10000)
        await self.page.fill(editor_selector, content)
        await asyncio.sleep(1)

        # Upload image if provided
        if image_path:
            await self._upload_image(image_path)

        # Click "Post" button
        post_button_selector = 'button[aria-label*="Post"]'
        await self.page.wait_for_selector(post_button_selector, timeout=10000)
        await self.page.click(post_button_selector)

        # Wait for post to be published
        await asyncio.sleep(3)

    async def _upload_image(self, image_path: str) -> None:
        """Upload image to post.

        Args:
            image_path: Path to image file.
        """
        if not self.page:
            raise Exception("Browser not initialized")

        # Click image upload button
        image_button_selector = 'button[aria-label*="Add a photo"]'
        await self.page.click(image_button_selector)
        await asyncio.sleep(1)

        # Upload file
        file_input_selector = 'input[type="file"]'
        await self.page.set_input_files(file_input_selector, image_path)
        await asyncio.sleep(2)  # Wait for upload

    async def _get_post_url(self) -> str:
        """Get URL of the published post.

        Returns:
            URL of the post.
        """
        # LinkedIn post URLs follow pattern: /feed/update/urn:li:activity:...
        # For now, return feed URL (actual post URL extraction would require
        # more complex logic to find the specific post)
        return "https://www.linkedin.com/feed/"

    async def _cleanup(self) -> None:
        """Clean up browser resources."""
        if self.page:
            await self.page.close()
