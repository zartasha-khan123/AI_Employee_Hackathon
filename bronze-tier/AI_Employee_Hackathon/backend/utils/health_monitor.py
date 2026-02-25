"""Health monitoring utilities for AI Employee services."""

from __future__ import annotations

import asyncio
import logging
import psutil
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from backend.utils.logging_utils import log_action
from backend.utils.timestamps import now_iso

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors health and resource usage of AI Employee services."""

    def __init__(self, vault_path: str | Path):
        """Initialize health monitor.

        Args:
            vault_path: Path to vault directory.
        """
        self.vault_path = Path(vault_path)
        self.process = psutil.Process()

        # Thresholds
        self.cpu_threshold = 80.0  # percent
        self.memory_threshold = 500  # MB

    async def check_health(self, service_name: str, task: asyncio.Task) -> dict[str, Any]:
        """Check health of a service task.

        Args:
            service_name: Name of the service.
            task: Asyncio task running the service.

        Returns:
            Health status dictionary.
        """
        status = {
            "service": service_name,
            "timestamp": now_iso(),
            "healthy": True,
            "status": "running",
            "warnings": [],
        }

        # Check if task is running
        if task.done():
            status["healthy"] = False
            status["status"] = "stopped"

            # Check if it crashed
            if task.exception():
                status["status"] = "crashed"
                status["error"] = str(task.exception())

        return status

    def get_resource_usage(self) -> dict[str, Any]:
        """Get current resource usage.

        Returns:
            Dictionary with CPU and memory usage.
        """
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            usage = {
                "timestamp": now_iso(),
                "cpu_percent": round(cpu_percent, 2),
                "memory_mb": round(memory_mb, 2),
                "warnings": [],
            }

            # Check thresholds
            if cpu_percent > self.cpu_threshold:
                usage["warnings"].append(f"CPU usage high: {cpu_percent}%")

            if memory_mb > self.memory_threshold:
                usage["warnings"].append(f"Memory usage high: {memory_mb} MB")

            return usage
        except Exception as e:
            logger.exception("Failed to get resource usage")
            return {
                "timestamp": now_iso(),
                "error": str(e),
                "warnings": ["Failed to get resource usage"],
            }

    def log_service_restart(self, service_name: str, reason: str) -> None:
        """Log service restart to vault.

        Args:
            service_name: Name of the service that restarted.
            reason: Reason for restart (e.g., "crashed", "manual").
        """
        log_dir = self.vault_path / "Logs" / "system"
        log_dir.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp": now_iso(),
            "service": service_name,
            "event": "restart",
            "reason": reason,
        }

        log_action(log_dir, entry)
        logger.warning(f"Service restart logged: {service_name} - {reason}")

    def log_resource_alert(self, alert_type: str, message: str, value: float) -> None:
        """Log resource usage alert.

        Args:
            alert_type: Type of alert (e.g., "cpu_high", "memory_high").
            message: Alert message.
            value: Current value that triggered alert.
        """
        log_dir = self.vault_path / "Logs" / "alerts"
        log_dir.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp": now_iso(),
            "alert_type": alert_type,
            "message": message,
            "value": value,
            "severity": "warning",
        }

        log_action(log_dir, entry)
        logger.warning(f"Resource alert: {message}")

    async def monitor_loop(
        self,
        services: dict[str, asyncio.Task],
        interval: int = 60,
    ) -> None:
        """Run continuous health monitoring loop.

        Args:
            services: Dictionary mapping service names to their tasks.
            interval: Check interval in seconds (default: 60).
        """
        logger.info("Health monitor started")

        while True:
            try:
                # Check service health
                for service_name, task in services.items():
                    health = await self.check_health(service_name, task)

                    if not health["healthy"]:
                        logger.error(f"Service unhealthy: {service_name} - {health['status']}")
                        self.log_service_restart(service_name, health.get("status", "unknown"))

                # Check resource usage
                usage = self.get_resource_usage()

                if usage.get("warnings"):
                    for warning in usage["warnings"]:
                        if "CPU" in warning:
                            self.log_resource_alert(
                                "cpu_high",
                                warning,
                                usage["cpu_percent"]
                            )
                        elif "Memory" in warning:
                            self.log_resource_alert(
                                "memory_high",
                                warning,
                                usage["memory_mb"]
                            )

                # Log metrics periodically
                if datetime.now(UTC).minute % 10 == 0:  # Every 10 minutes
                    self._log_metrics(usage)

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                logger.info("Health monitor stopped")
                break
            except Exception:
                logger.exception("Health monitor error")
                await asyncio.sleep(interval)

    def _log_metrics(self, usage: dict[str, Any]) -> None:
        """Log resource metrics to vault.

        Args:
            usage: Resource usage dictionary.
        """
        log_dir = self.vault_path / "Logs" / "metrics"
        log_dir.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp": usage["timestamp"],
            "cpu_percent": usage["cpu_percent"],
            "memory_mb": usage["memory_mb"],
        }

        log_action(log_dir, entry)
