"""Safety checker for email operations.

This module implements safety controls to prevent:
- Sending to non-approved recipients
- Leaking sensitive data (passwords, credit cards, SSN)
- Exceeding rate limits
- Sending risky bulk emails
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from backend.utils.timestamps import now_iso

logger = logging.getLogger(__name__)


class SafetyChecker:
    """Checks email safety before sending."""

    def __init__(self, allowed_recipients: list[str], dev_mode: bool = True):
        """Initialize the safety checker.

        Args:
            allowed_recipients: List of approved recipient email addresses.
            dev_mode: If True, allows all recipients (for testing).
        """
        self.allowed_recipients = [r.strip() for r in allowed_recipients if r.strip()]
        self.dev_mode = dev_mode
        self.logger = logging.getLogger(__name__)

        # Load rate limits
        self.rate_limits = self._load_rate_limits()
        self.send_history: list[dict[str, Any]] = []

    def _load_rate_limits(self) -> dict[str, Any]:
        """Load rate limits from config."""
        rate_limits_path = Path("config/rate_limits.json")

        if not rate_limits_path.exists():
            self.logger.warning("Rate limits config not found, using defaults")
            return {"email": {"per_hour": 10, "per_day": 50}}

        try:
            return json.loads(rate_limits_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            self.logger.warning("Invalid rate limits config, using defaults")
            return {"email": {"per_hour": 10, "per_day": 50}}

    def check_email(
        self, to: str, subject: str, body: str, cc: list[str]
    ) -> dict[str, Any]:
        """Check if email is safe to send.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Email body.
            cc: CC recipients.

        Returns:
            Dictionary with 'safe' boolean and 'reason' if blocked.
        """
        # Check recipient allowlist (skip in dev mode)
        if not self.dev_mode:
            if not self._is_recipient_allowed(to):
                return {
                    "safe": False,
                    "reason": "Recipient not in allowlist",
                    "details": f"{to} is not in ALLOWED_RECIPIENTS",
                }

            for cc_addr in cc:
                if not self._is_recipient_allowed(cc_addr):
                    return {
                        "safe": False,
                        "reason": "CC recipient not in allowlist",
                        "details": f"{cc_addr} is not in ALLOWED_RECIPIENTS",
                    }

        # Check for sensitive data in body
        sensitive_check = self._check_sensitive_data(body)
        if not sensitive_check["safe"]:
            return sensitive_check

        # Check rate limits
        rate_limit_check = self._check_rate_limits()
        if not rate_limit_check["safe"]:
            return rate_limit_check

        # Check bulk send (multiple recipients)
        if len(cc) > 5:
            return {
                "safe": False,
                "reason": "Bulk send detected",
                "details": f"Email has {len(cc)} CC recipients (max 5 without approval)",
            }

        # All checks passed
        self._record_send(to, cc)
        return {"safe": True}

    def _is_recipient_allowed(self, email: str) -> bool:
        """Check if recipient is in allowlist.

        Args:
            email: Email address to check.

        Returns:
            True if allowed, False otherwise.
        """
        if not self.allowed_recipients:
            # No allowlist configured - allow all (risky!)
            self.logger.warning("No recipient allowlist configured - allowing all recipients")
            return True

        email_lower = email.lower().strip()

        # Check exact match
        if email_lower in [r.lower() for r in self.allowed_recipients]:
            return True

        # Check domain match (e.g., "*@example.com")
        for allowed in self.allowed_recipients:
            if allowed.startswith("*@"):
                domain = allowed[2:].lower()
                if email_lower.endswith(f"@{domain}"):
                    return True

        return False

    def _check_sensitive_data(self, text: str) -> dict[str, Any]:
        """Check for sensitive data in text.

        Args:
            text: Text to check.

        Returns:
            Dictionary with 'safe' boolean and 'reason' if found.
        """
        # Password patterns
        if re.search(r"password[:\s]+\S+", text, re.IGNORECASE):
            return {
                "safe": False,
                "reason": "Sensitive data detected",
                "details": "Email contains password",
            }

        # Credit card patterns (basic check)
        if re.search(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", text):
            return {
                "safe": False,
                "reason": "Sensitive data detected",
                "details": "Email contains potential credit card number",
            }

        # SSN patterns
        if re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
            return {
                "safe": False,
                "reason": "Sensitive data detected",
                "details": "Email contains potential SSN",
            }

        # API keys (basic patterns)
        if re.search(r"(api[_-]?key|secret[_-]?key)[:\s]+\S+", text, re.IGNORECASE):
            return {
                "safe": False,
                "reason": "Sensitive data detected",
                "details": "Email contains potential API key",
            }

        return {"safe": True}

    def _check_rate_limits(self) -> dict[str, Any]:
        """Check if rate limits are exceeded.

        Returns:
            Dictionary with 'safe' boolean and 'reason' if exceeded.
        """
        now = now_iso()
        email_limits = self.rate_limits.get("email", {})
        per_hour = email_limits.get("per_hour", 10)
        per_day = email_limits.get("per_day", 50)

        # Count sends in last hour
        from backend.utils.timestamps import is_within_hours

        hour_sends = sum(
            1 for send in self.send_history if is_within_hours(send["timestamp"], 1)
        )

        if hour_sends >= per_hour:
            return {
                "safe": False,
                "reason": "Rate limit exceeded",
                "details": f"Sent {hour_sends} emails in last hour (limit: {per_hour})",
            }

        # Count sends in last day
        day_sends = sum(
            1 for send in self.send_history if is_within_hours(send["timestamp"], 24)
        )

        if day_sends >= per_day:
            return {
                "safe": False,
                "reason": "Rate limit exceeded",
                "details": f"Sent {day_sends} emails in last day (limit: {per_day})",
            }

        return {"safe": True}

    def _record_send(self, to: str, cc: list[str]) -> None:
        """Record an email send for rate limiting.

        Args:
            to: Recipient email address.
            cc: CC recipients.
        """
        self.send_history.append(
            {"timestamp": now_iso(), "to": to, "cc": cc, "count": 1 + len(cc)}
        )

        # Clean up old history (keep last 24 hours)
        from backend.utils.timestamps import is_within_hours

        self.send_history = [
            send for send in self.send_history if is_within_hours(send["timestamp"], 24)
        ]
