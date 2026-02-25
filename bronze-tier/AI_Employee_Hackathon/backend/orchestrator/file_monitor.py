"""File monitor using watchdog to detect vault changes.

This module monitors the vault directories for new files and changes,
triggering orchestrator actions when needed.
"""

import logging
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class VaultFileHandler(FileSystemEventHandler):
    """Handles file system events in the vault."""

    def __init__(self, on_new_action: Callable[[Path], None]):
        """Initialize the handler.

        Args:
            on_new_action: Callback function when new action file is detected.
        """
        super().__init__()
        self.on_new_action = on_new_action
        self._processing = set()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process markdown files in Needs_Action
        if file_path.suffix != ".md":
            return

        if "Needs_Action" not in file_path.parts:
            return

        # Avoid duplicate processing
        if str(file_path) in self._processing:
            return

        self._processing.add(str(file_path))
        logger.info("New action file detected: %s", file_path.name)

        try:
            self.on_new_action(file_path)
        finally:
            self._processing.discard(str(file_path))


class FileMonitor:
    """Monitors vault directories for changes."""

    def __init__(self, vault_path: str | Path):
        """Initialize the file monitor.

        Args:
            vault_path: Path to the vault directory.
        """
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.observer: Observer | None = None
        self.handler: VaultFileHandler | None = None
        self.logger = logging.getLogger(__name__)

    def start(self, on_new_action: Callable[[Path], None]) -> None:
        """Start monitoring the vault.

        Args:
            on_new_action: Callback function when new action file is detected.
        """
        if not self.needs_action.exists():
            self.needs_action.mkdir(parents=True, exist_ok=True)

        self.handler = VaultFileHandler(on_new_action)
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.needs_action), recursive=False)
        self.observer.start()
        self.logger.info("File monitor started, watching: %s", self.needs_action)

    def stop(self) -> None:
        """Stop monitoring the vault."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.logger.info("File monitor stopped")

    def get_existing_files(self) -> list[Path]:
        """Get list of existing action files in Needs_Action.

        Returns:
            List of markdown file paths.
        """
        if not self.needs_action.exists():
            return []

        return sorted(self.needs_action.glob("*.md"))
