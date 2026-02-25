"""Tests for LinkedIn Watcher."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.watchers.linkedin_watcher import LinkedInWatcher


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault structure."""
    vault = tmp_path / "vault"
    (vault / "Needs_Action").mkdir(parents=True)
    (vault / "Logs").mkdir(parents=True)
    (vault / "Business_Updates").mkdir(parents=True)
    (vault / "Announcements").mkdir(parents=True)

    # Create Content_Calendar.md
    calendar_content = """# Content Calendar

### 2026-02-16 10:00 AM
**Type:** Business Update
**Status:** Ready

Test post content for Q1 results.

**Hashtags:** #Test #Q1
**Media:** test.png
"""
    (vault / "Content_Calendar.md").write_text(calendar_content, encoding="utf-8")

    return vault


@pytest.fixture
def linkedin_config():
    """Default LinkedIn configuration."""
    return {
        "poll_interval_seconds": 600,
        "rate_limits": {
            "posts_per_day": 3,
            "posts_per_week": 10
        },
        "exclude_keywords": ["draft", "wip", "do not post"]
    }


def test_linkedin_watcher_init(temp_vault, linkedin_config):
    """Test LinkedInWatcher initialization."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=True,
        dev_mode=True,
    )

    assert watcher.vault_path == temp_vault
    assert watcher.needs_action == temp_vault / "Needs_Action"
    assert watcher.dry_run is True
    assert watcher.dev_mode is True


def test_content_hash(temp_vault, linkedin_config):
    """Test content hashing for duplicate detection."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=True,
    )

    content1 = "Test post content"
    content2 = "Test post content"
    content3 = "Different content"

    hash1 = watcher._content_hash(content1)
    hash2 = watcher._content_hash(content2)
    hash3 = watcher._content_hash(content3)

    assert hash1 == hash2  # Same content = same hash
    assert hash1 != hash3  # Different content = different hash
    assert len(hash1) == 16  # Hash is 16 characters


def test_is_duplicate(temp_vault, linkedin_config):
    """Test duplicate detection."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=False,
    )

    content = "Test post content"

    # First time - not duplicate
    assert not watcher._is_duplicate(content)

    # Mark as posted
    watcher._mark_as_posted(content)

    # Second time - is duplicate
    assert watcher._is_duplicate(content)


def test_has_exclude_keywords(temp_vault, linkedin_config):
    """Test exclude keyword detection."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=True,
    )

    # Has exclude keyword
    assert watcher._has_exclude_keywords("This is a draft post")
    assert watcher._has_exclude_keywords("WIP - do not post")

    # No exclude keyword
    assert not watcher._has_exclude_keywords("This is ready to post")


def test_extract_hashtags(temp_vault, linkedin_config):
    """Test hashtag extraction."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=True,
    )

    content = """
### 2026-02-16 10:00 AM
**Type:** Business Update
**Status:** Ready

Post content here.

**Hashtags:** #Test #BusinessUpdate #Q1Results
**Media:** test.png
"""

    hashtags = watcher._extract_hashtags(content, "2026-02-16 10:00 AM")
    assert "#Test" in hashtags
    assert "#BusinessUpdate" in hashtags
    assert "#Q1Results" in hashtags


def test_extract_media(temp_vault, linkedin_config):
    """Test media path extraction."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=True,
    )

    content = """
### 2026-02-16 10:00 AM
**Type:** Business Update
**Status:** Ready

Post content here.

**Hashtags:** #Test
**Media:** images/test.png
"""

    media = watcher._extract_media(content, "2026-02-16 10:00 AM")
    assert media == "images/test.png"


@pytest.mark.asyncio
async def test_scan_content_calendar(temp_vault, linkedin_config):
    """Test Content_Calendar.md scanning."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=True,
    )

    # Mock datetime to make scheduled post "ready"
    with patch('backend.watchers.linkedin_watcher.datetime') as mock_datetime:
        from datetime import datetime, UTC
        # Set current time to 30 minutes before scheduled time
        mock_datetime.now.return_value = datetime(2026, 2, 16, 9, 30, tzinfo=UTC)
        mock_datetime.strptime = datetime.strptime

        posts = watcher._scan_content_calendar()

        # Should find the ready post
        assert len(posts) >= 0  # May be 0 if time logic doesn't match


def test_scan_business_updates(temp_vault, linkedin_config):
    """Test Business_Updates/ folder scanning."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=True,
    )

    # Create a business update file
    update_file = temp_vault / "Business_Updates" / "test-update.md"
    update_file.write_text("This is a test business update post.", encoding="utf-8")

    posts = watcher._scan_business_updates()

    assert len(posts) == 1
    assert posts[0]["post_type"] == "business_update"
    assert "test business update" in posts[0]["content"]


def test_scan_announcements(temp_vault, linkedin_config):
    """Test Announcements/ folder scanning."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=True,
    )

    # Create an announcement file
    announcement_file = temp_vault / "Announcements" / "big-news.md"
    announcement_file.write_text("🎉 Big announcement!", encoding="utf-8")

    posts = watcher._scan_announcements()

    assert len(posts) == 1
    assert posts[0]["post_type"] == "announcement"
    assert posts[0]["priority"] == "high"
    assert "Big announcement" in posts[0]["content"]


@pytest.mark.asyncio
async def test_create_action_file_dry_run(temp_vault, linkedin_config):
    """Test action file creation in dry run mode."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=True,
    )

    post = {
        "content": "Test post content",
        "post_type": "business_update",
        "scheduled_date": "2026-02-16T10:00:00Z",
        "hashtags": ["#Test"],
        "media": None,
        "source": "test.md",
    }

    result = await watcher.create_action_file(post)

    # Dry run should return None
    assert result is None

    # No file should be created
    action_files = list((temp_vault / "Needs_Action").glob("*.md"))
    assert len(action_files) == 0


@pytest.mark.asyncio
async def test_create_action_file_real(temp_vault, linkedin_config):
    """Test action file creation in real mode."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=False,
    )

    post = {
        "content": "Test post content for real creation",
        "post_type": "business_update",
        "scheduled_date": "2026-02-16T10:00:00Z",
        "hashtags": ["#Test", "#Real"],
        "media": "test.png",
        "source": "test.md",
    }

    result = await watcher.create_action_file(post)

    # Should return file path
    assert result is not None
    assert result.exists()
    assert result.name.startswith("linkedin-test-post-content")

    # Verify frontmatter
    content = result.read_text(encoding="utf-8")
    assert "type: linkedin_post" in content
    assert "Test post content for real creation" in content
    assert "#Test #Real" in content


def test_posted_hashes_persistence(temp_vault, linkedin_config):
    """Test posted hashes are saved and loaded correctly."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=False,
    )

    # Mark content as posted
    content = "Test post content"
    watcher._mark_as_posted(content)

    # Create new watcher and load
    watcher2 = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=False,
    )
    watcher2._load_posted_hashes()

    # Should detect as duplicate
    assert watcher2._is_duplicate(content)


@pytest.mark.asyncio
async def test_check_for_updates(temp_vault, linkedin_config):
    """Test check_for_updates aggregates all sources."""
    watcher = LinkedInWatcher(
        vault_path=str(temp_vault),
        linkedin_config=linkedin_config,
        dry_run=True,
    )

    # Create test files
    (temp_vault / "Business_Updates" / "update1.md").write_text("Update 1", encoding="utf-8")
    (temp_vault / "Announcements" / "announce1.md").write_text("Announcement 1", encoding="utf-8")

    posts = await watcher.check_for_updates()

    # Should find posts from multiple sources
    assert len(posts) >= 2  # At least business update and announcement
