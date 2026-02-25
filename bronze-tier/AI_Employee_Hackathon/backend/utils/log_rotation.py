"""Enhanced logging utilities with rotation and metrics."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any

from backend.utils.timestamps import today_iso

logger = logging.getLogger(__name__)


def rotate_logs(log_dir: str | Path, retention_days: int = 90) -> int:
    """Rotate logs by deleting files older than retention period.

    Args:
        log_dir: Path to the log directory.
        retention_days: Number of days to retain logs (default: 90).

    Returns:
        Number of log files deleted.

    Examples:
        >>> deleted = rotate_logs("vault/Logs/actions", 90)
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return 0

    cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
    deleted_count = 0

    for log_file in log_path.glob("*.json"):
        try:
            # Parse date from filename (YYYY-MM-DD.json)
            file_date_str = log_file.stem
            file_date = datetime.fromisoformat(file_date_str).replace(tzinfo=UTC)

            if file_date < cutoff_date:
                log_file.unlink()
                deleted_count += 1
                logger.info(f"Rotated old log file: {log_file.name}")
        except (ValueError, OSError) as e:
            logger.warning(f"Failed to rotate {log_file.name}: {e}")

    return deleted_count


def calculate_metrics(log_dir: str | Path, days: int = 1) -> dict[str, Any]:
    """Calculate activity metrics from logs.

    Args:
        log_dir: Path to the log directory.
        days: Number of days to analyze (default: 1).

    Returns:
        Dictionary with metrics:
        - total_actions: Total number of actions
        - success_rate: Percentage of successful actions
        - error_count: Number of errors
        - avg_duration_ms: Average action duration
        - actions_by_type: Count by action type

    Examples:
        >>> metrics = calculate_metrics("vault/Logs/actions", days=7)
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return _empty_metrics()

    # Get log files for the specified period
    cutoff_date = datetime.now(UTC) - timedelta(days=days)
    entries = []

    for log_file in sorted(log_path.glob("*.json")):
        try:
            file_date_str = log_file.stem
            file_date = datetime.fromisoformat(file_date_str).replace(tzinfo=UTC)

            if file_date >= cutoff_date:
                data = json.loads(log_file.read_text(encoding="utf-8"))
                entries.extend(data.get("entries", []))
        except (ValueError, json.JSONDecodeError, OSError):
            continue

    if not entries:
        return _empty_metrics()

    # Calculate metrics
    total_actions = len(entries)
    success_count = sum(1 for e in entries if e.get("result") == "success")
    error_count = sum(1 for e in entries if e.get("result") == "error")
    success_rate = (success_count / total_actions * 100) if total_actions > 0 else 0

    # Calculate average duration
    durations = [e.get("duration_ms", 0) for e in entries if "duration_ms" in e]
    avg_duration_ms = sum(durations) / len(durations) if durations else 0

    # Count by action type
    actions_by_type: dict[str, int] = {}
    for entry in entries:
        action_type = entry.get("action_type", "unknown")
        actions_by_type[action_type] = actions_by_type.get(action_type, 0) + 1

    return {
        "total_actions": total_actions,
        "success_count": success_count,
        "error_count": error_count,
        "success_rate": round(success_rate, 2),
        "avg_duration_ms": round(avg_duration_ms, 2),
        "actions_by_type": actions_by_type,
        "period_days": days,
    }


def _empty_metrics() -> dict[str, Any]:
    """Return empty metrics structure."""
    return {
        "total_actions": 0,
        "success_count": 0,
        "error_count": 0,
        "success_rate": 0.0,
        "avg_duration_ms": 0.0,
        "actions_by_type": {},
        "period_days": 0,
    }


def get_error_summary(log_dir: str | Path, hours: int = 24) -> list[dict[str, Any]]:
    """Get summary of recent errors for alerting.

    Args:
        log_dir: Path to the log directory.
        hours: Number of hours to look back (default: 24).

    Returns:
        List of error entries with timestamp, actor, action_type, and error message.

    Examples:
        >>> errors = get_error_summary("vault/Logs/actions", hours=24)
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return []

    cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
    errors = []

    # Get recent log files
    for log_file in sorted(log_path.glob("*.json"), reverse=True):
        try:
            data = json.loads(log_file.read_text(encoding="utf-8"))
            for entry in data.get("entries", []):
                if entry.get("result") == "error":
                    # Parse timestamp
                    timestamp_str = entry.get("timestamp", "")
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        if timestamp >= cutoff_time:
                            errors.append({
                                "timestamp": timestamp_str,
                                "actor": entry.get("actor", "unknown"),
                                "action_type": entry.get("action_type", "unknown"),
                                "target": entry.get("target", ""),
                                "error": entry.get("parameters", {}).get("error", "Unknown error"),
                            })
                    except ValueError:
                        continue
        except (json.JSONDecodeError, OSError):
            continue

    return sorted(errors, key=lambda x: x["timestamp"], reverse=True)


def log_performance_metric(
    log_dir: str | Path,
    metric_name: str,
    value: float,
    unit: str = "ms",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log a performance metric.

    Args:
        log_dir: Path to the metrics log directory.
        metric_name: Name of the metric (e.g., "api_latency", "memory_usage").
        value: Metric value.
        unit: Unit of measurement (e.g., "ms", "MB", "count").
        metadata: Optional additional metadata.

    Examples:
        >>> log_performance_metric(
        ...     "vault/Logs/metrics",
        ...     "email_send_duration",
        ...     1250.5,
        ...     "ms",
        ...     {"recipient_count": 1}
        ... )
    """
    from backend.utils.timestamps import now_iso
    from backend.utils.uuid_utils import correlation_id

    entry = {
        "timestamp": now_iso(),
        "correlation_id": correlation_id(),
        "metric_name": metric_name,
        "value": value,
        "unit": unit,
        "metadata": metadata or {},
    }

    from backend.utils.logging_utils import log_action

    log_action(log_dir, entry)
