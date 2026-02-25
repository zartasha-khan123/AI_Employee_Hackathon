"""Safety checks for payment processing."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PaymentSafetyError(Exception):
    """Raised when payment fails safety checks."""
    pass


def validate_payment_safety(
    amount: float,
    currency: str,
    recipient: str,
    description: str,
    vault_path: str = "./vault",
    allowed_recipients: list[str] | None = None,
    max_amount: float = 1000.0,
    secondary_approval_threshold: float = 100.0,
) -> dict[str, Any]:
    """Validate payment against safety rules.

    Args:
        amount: Payment amount
        currency: Currency code
        recipient: Recipient identifier
        description: Payment description
        vault_path: Path to vault for duplicate detection
        allowed_recipients: List of allowed recipient emails/IDs
        max_amount: Maximum allowed payment amount
        secondary_approval_threshold: Amount requiring secondary approval

    Returns:
        Safety check result with warnings and requirements

    Raises:
        PaymentSafetyError: If payment fails critical safety checks
    """
    warnings = []
    requirements = []

    # 1. Amount validation
    if amount <= 0:
        raise PaymentSafetyError(f"Invalid amount: {amount}")

    if amount > max_amount:
        raise PaymentSafetyError(
            f"Amount {amount} {currency} exceeds maximum allowed: "
            f"{max_amount} {currency}"
        )

    if amount >= secondary_approval_threshold:
        requirements.append("secondary_approval")
        warnings.append(
            f"Amount {amount} {currency} requires secondary approval "
            f"(threshold: {secondary_approval_threshold})"
        )

    # 2. Currency validation
    valid_currencies = ["USD", "EUR", "GBP", "CAD", "AUD"]
    if currency.upper() not in valid_currencies:
        raise PaymentSafetyError(
            f"Unsupported currency: {currency}. "
            f"Allowed: {', '.join(valid_currencies)}"
        )

    # 3. Recipient validation
    if allowed_recipients:
        if recipient not in allowed_recipients:
            raise PaymentSafetyError(
                f"Recipient not in allowlist: {recipient}. "
                f"Add to ALLOWED_PAYMENT_RECIPIENTS in .env"
            )

    # Validate email format if recipient looks like email
    if "@" in recipient:
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, recipient):
            raise PaymentSafetyError(f"Invalid recipient email format: {recipient}")

    # 4. Description validation
    if not description or len(description.strip()) < 5:
        raise PaymentSafetyError(
            "Payment description too short. Provide clear reason for payment."
        )

    # Check for prohibited keywords
    prohibited_keywords = [
        "test", "fake", "dummy", "sample", "xxx",
        "hack", "exploit", "fraud", "scam"
    ]
    description_lower = description.lower()
    for keyword in prohibited_keywords:
        if keyword in description_lower:
            warnings.append(
                f"Description contains potentially problematic keyword: '{keyword}'"
            )

    # 5. Duplicate detection
    duplicate_check = _check_duplicate_payment(
        amount, recipient, description, vault_path
    )
    if duplicate_check["is_duplicate"]:
        warnings.append(
            f"Possible duplicate payment detected: "
            f"{duplicate_check['similar_count']} similar transaction(s) "
            f"in last {duplicate_check['window_hours']} hours"
        )
        requirements.append("duplicate_confirmation")

    # 6. Sensitive data detection
    sensitive_patterns = {
        "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
        "Credit Card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        "API Key": r"\b[A-Za-z0-9]{32,}\b",
    }

    for data_type, pattern in sensitive_patterns.items():
        if re.search(pattern, description):
            raise PaymentSafetyError(
                f"Description contains {data_type}. "
                f"Never include sensitive data in payment descriptions."
            )

    return {
        "safe": len(warnings) == 0,
        "warnings": warnings,
        "requirements": requirements,
        "checks_passed": {
            "amount_valid": True,
            "currency_valid": True,
            "recipient_valid": True,
            "description_valid": True,
            "no_duplicates": not duplicate_check["is_duplicate"],
            "no_sensitive_data": True,
        }
    }


def _check_duplicate_payment(
    amount: float,
    recipient: str,
    description: str,
    vault_path: str,
    window_hours: int = 24
) -> dict[str, Any]:
    """Check for duplicate payments in recent history.

    Args:
        amount: Payment amount
        recipient: Recipient identifier
        description: Payment description
        vault_path: Path to vault
        window_hours: Time window to check for duplicates

    Returns:
        Duplicate check result
    """
    try:
        logs_dir = Path(vault_path) / "Logs" / "actions"
        if not logs_dir.exists():
            return {"is_duplicate": False, "similar_count": 0, "window_hours": window_hours}

        cutoff_time = datetime.now() - timedelta(hours=window_hours)
        similar_count = 0

        # Check recent payment logs
        for log_file in logs_dir.glob("payment_*.md"):
            try:
                # Check file modification time
                if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff_time:
                    continue

                content = log_file.read_text(encoding="utf-8")

                # Simple similarity check
                if (
                    str(amount) in content
                    and recipient in content
                    and description[:20] in content
                ):
                    similar_count += 1

            except Exception:
                continue

        return {
            "is_duplicate": similar_count > 0,
            "similar_count": similar_count,
            "window_hours": window_hours
        }

    except Exception as e:
        logger.warning(f"Duplicate check failed: {e}")
        return {"is_duplicate": False, "similar_count": 0, "window_hours": window_hours}


def check_rate_limit(
    vault_path: str = "./vault",
    limit_per_hour: int = 3,
    limit_per_day: int = 10
) -> dict[str, Any]:
    """Check payment rate limits.

    Args:
        vault_path: Path to vault
        limit_per_hour: Maximum payments per hour
        limit_per_day: Maximum payments per day

    Returns:
        Rate limit status

    Raises:
        PaymentSafetyError: If rate limit exceeded
    """
    try:
        logs_dir = Path(vault_path) / "Logs" / "actions"
        if not logs_dir.exists():
            return {"within_limits": True, "count_hour": 0, "count_day": 0}

        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        count_hour = 0
        count_day = 0

        for log_file in logs_dir.glob("payment_*.md"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

                if mtime >= hour_ago:
                    count_hour += 1
                if mtime >= day_ago:
                    count_day += 1

            except Exception:
                continue

        if count_hour >= limit_per_hour:
            raise PaymentSafetyError(
                f"Rate limit exceeded: {count_hour} payments in last hour "
                f"(limit: {limit_per_hour}/hour)"
            )

        if count_day >= limit_per_day:
            raise PaymentSafetyError(
                f"Rate limit exceeded: {count_day} payments in last day "
                f"(limit: {limit_per_day}/day)"
            )

        return {
            "within_limits": True,
            "count_hour": count_hour,
            "count_day": count_day,
            "limit_hour": limit_per_hour,
            "limit_day": limit_per_day
        }

    except PaymentSafetyError:
        raise
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
        return {"within_limits": True, "count_hour": 0, "count_day": 0}
