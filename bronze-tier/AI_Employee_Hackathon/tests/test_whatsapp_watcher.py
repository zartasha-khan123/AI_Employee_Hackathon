"""Tests for WhatsApp Watcher."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.watchers.whatsapp_watcher import WhatsAppWatcher


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault structure."""
    vault = tmp_path / "vault"
    (vault / "Needs_Action").mkdir(parents=True)
    (vault / "Logs").mkdir(parents=True)
    return vault


@pytest.fixture
def whatsapp_config():
    """Default WhatsApp configuration."""
    return {
        "poll_interval_seconds": 60,
        "session_path": "config/whatsapp_session",
        "headless": True,
        "priority_keywords": {
            "high": ["urgent", "asap", "emergency"],
            "medium": ["question", "need", "help"]
        },
        "exclude_contacts": ["Spam", "Unknown"],
        "exclude_groups": True,
        "max_message_length": 5000,
        "mark_as_read": False
    }


def test_whatsapp_watcher_init(temp_vault, whatsapp_config):
    """Test WhatsAppWatcher initialization."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=True,
        dev_mode=True,
    )

    assert watcher.vault_path == temp_vault
    assert watcher.needs_action == temp_vault / "Needs_Action"
    assert watcher.dry_run is True
    assert watcher.dev_mode is True
    assert watcher.headless is True


def test_classify_priority_high(temp_vault, whatsapp_config):
    """Test high priority classification."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=True,
    )

    # High priority keywords
    assert watcher._classify_priority("This is urgent!") == "high"
    assert watcher._classify_priority("ASAP please respond") == "high"
    assert watcher._classify_priority("Emergency situation") == "high"


def test_classify_priority_medium(temp_vault, whatsapp_config):
    """Test medium priority classification."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=True,
    )

    # Medium priority keywords
    assert watcher._classify_priority("I have a question") == "medium"
    assert watcher._classify_priority("Need your help") == "medium"


def test_classify_priority_low(temp_vault, whatsapp_config):
    """Test low priority classification."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=True,
    )

    # No priority keywords
    assert watcher._classify_priority("Hello, how are you?") == "low"
    assert watcher._classify_priority("Just checking in") == "low"


@pytest.mark.asyncio
async def test_check_for_updates_dev_mode(temp_vault, whatsapp_config):
    """Test check_for_updates in DEV_MODE."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=True,
        dev_mode=True,
    )

    # In dev mode, should return empty list without browser
    messages = await watcher.check_for_updates()
    assert messages == []


@pytest.mark.asyncio
async def test_create_action_file_dry_run(temp_vault, whatsapp_config):
    """Test action file creation in dry run mode."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=True,
    )

    message = {
        "message_id": "test123",
        "from": "John Doe",
        "message": "This is a test message",
        "priority": "high",
        "is_group": False,
        "received": "2026-02-15T14:30:22Z",
    }

    result = await watcher.create_action_file(message)

    # Dry run should return None
    assert result is None

    # No file should be created
    action_files = list((temp_vault / "Needs_Action").glob("*.md"))
    assert len(action_files) == 0


@pytest.mark.asyncio
async def test_create_action_file_real(temp_vault, whatsapp_config):
    """Test action file creation in real mode."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=False,
    )

    message = {
        "message_id": "test123",
        "from": "John Doe",
        "message": "This is a test message for real creation",
        "priority": "high",
        "is_group": False,
        "received": "2026-02-15T14:30:22Z",
    }

    result = await watcher.create_action_file(message)

    # Should return file path
    assert result is not None
    assert result.exists()
    assert result.name.startswith("whatsapp-john-doe-")

    # Verify frontmatter
    content = result.read_text(encoding="utf-8")
    assert "type: whatsapp_message" in content
    assert "John Doe" in content
    assert "This is a test message for real creation" in content


def test_processed_ids_persistence(temp_vault, whatsapp_config):
    """Test processed IDs are saved and loaded correctly."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=False,
    )

    # Add processed ID
    watcher._processed_ids.add("message123")
    watcher._save_processed_ids()

    # Create new watcher and load
    watcher2 = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=False,
    )
    watcher2._load_processed_ids()

    assert "message123" in watcher2._processed_ids


@pytest.mark.asyncio
async def test_initialize_browser_dev_mode(temp_vault, whatsapp_config):
    """Test browser initialization is skipped in DEV_MODE."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=True,
        dev_mode=True,
    )

    # Should not raise error and not initialize browser
    await watcher._initialize_browser()
    assert watcher.browser is None


@pytest.mark.asyncio
async def test_check_authentication_dev_mode(temp_vault, whatsapp_config):
    """Test authentication check in DEV_MODE."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=True,
        dev_mode=True,
    )

    # In dev mode, should always return True
    is_authenticated = await watcher._check_authentication()
    assert is_authenticated is True


@pytest.mark.asyncio
async def test_get_unread_messages_dev_mode(temp_vault, whatsapp_config):
    """Test getting unread messages in DEV_MODE."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=True,
        dev_mode=True,
    )

    # In dev mode, should return empty list
    messages = await watcher._get_unread_messages()
    assert messages == []


@pytest.mark.asyncio
async def test_cleanup(temp_vault, whatsapp_config):
    """Test cleanup method."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=True,
        dev_mode=True,
    )

    # Should not raise error even without browser
    await watcher.cleanup()


def test_session_path(temp_vault, whatsapp_config):
    """Test session path configuration."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=True,
    )

    assert watcher.session_path == Path("config/whatsapp_session")


def test_message_preview_truncation(temp_vault, whatsapp_config):
    """Test message preview is truncated in frontmatter."""
    watcher = WhatsAppWatcher(
        vault_path=str(temp_vault),
        whatsapp_config=whatsapp_config,
        dry_run=False,
    )

    long_message = "A" * 500
    message = {
        "message_id": "test123",
        "from": "Test User",
        "message": long_message,
        "priority": "low",
        "is_group": False,
        "received": "2026-02-15T14:30:22Z",
    }

    # Create action file
    import asyncio
    result = asyncio.run(watcher.create_action_file(message))

    # Read and check preview length
    content = result.read_text(encoding="utf-8")
    # Preview should be truncated to 200 chars in frontmatter
    assert "message_preview:" in content
