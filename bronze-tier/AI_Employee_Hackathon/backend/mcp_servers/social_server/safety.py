"""Safety checks for social media posts."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


class SocialSafetyChecker:
    """Performs safety checks on social media content."""

    # Patterns for sensitive content
    SENSITIVE_PATTERNS = [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b\d{16}\b",  # Credit card
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email (may be intentional)
        r"\b(?:password|passwd|pwd)[\s:=]+\S+",  # Passwords
    ]

    # Prohibited content
    PROHIBITED_KEYWORDS = [
        "confidential",
        "internal only",
        "do not share",
        "private",
        "secret",
    ]

    def check_content(self, content: str) -> tuple[bool, list[str]]:
        """Check if content is safe to post.

        Args:
            content: Post content to check.

        Returns:
            Tuple of (is_safe, list_of_warnings).
        """
        warnings = []

        # Check for sensitive patterns
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(f"Potential sensitive data detected: {pattern}")

        # Check for prohibited keywords
        content_lower = content.lower()
        for keyword in self.PROHIBITED_KEYWORDS:
            if keyword in content_lower:
                warnings.append(f"Prohibited keyword detected: {keyword}")

        # Check length
        if len(content) > 3000:
            warnings.append("Content exceeds LinkedIn character limit (3000)")

        is_safe = len(warnings) == 0
        return is_safe, warnings

    def sanitize_content(self, content: str) -> str:
        """Remove or redact sensitive information from content.

        Args:
            content: Original content.

        Returns:
            Sanitized content.
        """
        sanitized = content

        # Redact SSN
        sanitized = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "XXX-XX-XXXX", sanitized)

        # Redact credit card
        sanitized = re.sub(r"\b\d{16}\b", "XXXX-XXXX-XXXX-XXXX", sanitized)

        # Redact passwords
        sanitized = re.sub(
            r"\b(?:password|passwd|pwd)[\s:=]+\S+",
            "password: [REDACTED]",
            sanitized,
            flags=re.IGNORECASE,
        )

        return sanitized
