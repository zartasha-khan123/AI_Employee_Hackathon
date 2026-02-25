"""Tests for Calendar Watcher."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.watchers.calendar_watcher import CalendarWatcher


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault structure."""
    vault = tmp_path / "vault"
    (vault / "Needs_Action").mkdir(parents=True)
    (vault / "Logs").mkdir(parents=True)
    return vault


@pytest.fixture
def calendar_config():
    """Default calendar configuration."""
    return {
        "lookahead_hours": 48,
        "preparation_threshold_hours": 2,
        "priority_keywords": {
            "high": ["urgent", "board", "client"],
            "medium": ["review", "sync"],
        },
        "exclude_event_types": ["lunch", "break"],
        "vip_domains": ["client.com"],
        "processed_ids_retention_days": 7,
    }


@pytest.fixture
def mock_calendar_service():
    """Mock Google Calendar API service."""
    service = MagicMock()
    return service


def test_calendar_watcher_init(temp_vault, calendar_config):
    """Test CalendarWatcher initialization."""
    watcher = CalendarWatcher(
        vault_path=str(temp_vault),
        calendar_config=calendar_config,
        dry_run=True,
        dev_mode=True,
    )

    assert watcher.vault_path == temp_vault
    assert watcher.needs_action == temp_vault / "Needs_Action"
    assert watcher.dry_run is True
    assert watcher.dev_mode is True


def test_requires_preparation_with_keywords(temp_vault, calendar_config):
    """Test event requires preparation based on keywords."""
    watcher = CalendarWatcher(
        vault_path=str(temp_vault),
        calendar_config=calendar_config,
        dry_run=True,
    )

    # Event with preparation keyword
    assert watcher._requires_preparation(
        "Please prepare presentation",
        "Review slides",
        ["user@example.com"],
        datetime.now(UTC).isoformat(),
    )

    # Event without preparation keyword
    assert not watcher._requires_preparation(
        "Quick sync",
        "Casual chat",
        [],
        datetime.now(UTC).isoformat(),
    )


def test_requires_preparation_with_external_attendees(temp_vault, calendar_config):
    """Test event requires preparation with external attendees."""
    watcher = CalendarWatcher(
        vault_path=str(temp_vault),
        calendar_config=calendar_config,
        dry_run=True,
    )

    # Multiple attendees (external meeting)
    assert watcher._requires_preparation(
        "Team meeting",
        "Discussion",
        ["user1@example.com", "user2@example.com"],
        datetime.now(UTC).isoformat(),
    )


def test_requires_preparation_time_proximity(temp_vault, calendar_config):
    """Test event requires preparation based on time proximity."""
    watcher = CalendarWatcher(
        vault_path=str(temp_vault),
        calendar_config=calendar_config,
        dry_run=True,
    )

    # Event in 1 hour (within threshold)
    soon = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    assert watcher._requires_preparation("Meeting", "", [], soon)

    # Event in 24 hours (outside threshold)
    later = (datetime.now(UTC) + timedelta(hours=24)).isoformat()
    assert not watcher._requires_preparation("Meeting", "", [], later)


def test_classify_priority_high(temp_vault, calendar_config):
    """Test high priority classification."""
    watcher = CalendarWatcher(
        vault_path=str(temp_vault),
        calendar_config=calendar_config,
        dry_run=True,
    )

    # High priority keyword
    priority = watcher._classify_priority(
        "Urgent client meeting",
        "",
        [],
        datetime.now(UTC).isoformat(),
        ["client.com"],
    )
    assert priority == "high"

    # VIP domain attendee
    priority = watcher._classify_priority(
        "Meeting",
        "",
        ["contact@client.com"],
        datetime.now(UTC).isoformat(),
        ["client.com"],
    )
    assert priority == "high"

    # Time proximity (< 2 hours)
    soon = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    priority = watcher._classify_priority("Meeting", "", [], soon, [])
    assert priority == "high"


def test_classify_priority_medium(temp_vault, calendar_config):
    """Test medium priority classification."""
    watcher = CalendarWatcher(
        vault_path=str(temp_vault),
        calendar_config=calendar_config,
        dry_run=True,
    )

    priority = watcher._classify_priority(
        "Code review session",
        "",
        [],
        datetime.now(UTC).isoformat(),
        [],
    )
    assert priority == "medium"


def test_classify_priority_low(temp_vault, calendar_config):
    """Test low priority classification."""
    watcher = CalendarWatcher(
        vault_path=str(temp_vault),
        calendar_config=calendar_config,
        dry_run=True,
    )

    priority = watcher._classify_priority(
        "Casual chat",
        "",
        [],
        datetime.now(UTC).isoformat(),
        [],
    )
    assert priority == "low"


def test_is_excluded_event(temp_vault, calendar_config):
    """Test event exclusion patterns."""
    watcher = CalendarWatcher(
        vault_path=str(temp_vault),
        calendar_config=calendar_config,
        dry_run=True,
    )

    # Excluded event
    assert watcher._is_excluded_event("Lunch break", "", ["lunch", "break"])

    # Not excluded
    assert not watcher._is_excluded_event("Team meeting", "", ["lunch", "break"])


@pytest.mark.asyncio
async def test_create_action_file_dry_run(temp_vault, calendar_config):
    """Test action file creation in dry run mode."""
    watcher = CalendarWatcher(
        vault_path=str(temp_vault),
        calendar_config=calendar_config,
        dry_run=True,
    )

    event = {
        "event_id": "test123",
        "summary": "Client Demo",
        "description": "Product review",
        "start_time": "2026-02-16T14:00:00Z",
        "end_time": "2026-02-16T15:00:00Z",
        "attendees": ["client@example.com"],
        "priority": "high",
        "requires_preparation": True,
        "location": "Conference Room A",
        "html_link": "https://calendar.google.com/event?eid=test123",
    }

    result = await watcher.create_action_file(event)

    # Dry run should return None
    assert result is None

    # No file should be created
    action_files = list((temp_vault / "Needs_Action").glob("*.md"))
    assert len(action_files) == 0


@pytest.mark.asyncio
async def test_create_action_file_real(temp_vault, calendar_config):
    """Test action file creation in real mode."""
    watcher = CalendarWatcher(
        vault_path=str(temp_vault),
        calendar_config=calendar_config,
        dry_run=False,
    )

    event = {
        "event_id": "test123",
        "summary": "Client Demo",
        "description": "Product review",
        "start_time": "2026-02-16T14:00:00Z",
        "end_time": "2026-02-16T15:00:00Z",
        "attendees": ["client@example.com"],
        "priority": "high",
        "requires_preparation": True,
        "location": "Conference Room A",
        "html_link": "https://calendar.google.com/event?eid=test123",
    }

    result = await watcher.create_action_file(event)

    # Should return file path
    assert result is not None
    assert result.exists()
    assert result.name.startswith("calendar-client-demo-")

    # Verify frontmatter
    content = result.read_text(encoding="utf-8")
    assert "type: calendar_event" in content
    assert "Client Demo" in content
    assert "client@example.com" in content


def test_processed_ids_persistence(temp_vault, calendar_config):
    """Test processed IDs are saved and loaded correctly."""
    watcher = CalendarWatcher(
        vault_path=str(temp_vault),
        calendar_config=calendar_config,
        dry_run=False,
    )

    # Add processed ID
    watcher._processed_ids = {"event123": "2026-02-15T14:00:00Z"}
    watcher._save_processed_ids()

    # Create new watcher and load
    watcher2 = CalendarWatcher(
        vault_path=str(temp_vault),
        calendar_config=calendar_config,
        dry_run=False,
    )
    watcher2._load_processed_ids()

    assert "event123" in watcher2._processed_ids
    assert watcher2._processed_ids["event123"] == "2026-02-15T14:00:00Z"
