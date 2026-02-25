"""Email sender - SMTP integration for sending emails.

This module handles the actual SMTP connection and email sending,
with support for DEV_MODE simulation.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from backend.utils.timestamps import now_iso
from backend.utils.uuid_utils import short_id

logger = logging.getLogger(__name__)


class EmailSender:
    """Handles SMTP email sending with DEV_MODE support."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        dev_mode: bool = True,
    ):
        """Initialize the email sender.

        Args:
            smtp_host: SMTP server hostname.
            smtp_port: SMTP server port.
            smtp_user: SMTP username (email address).
            smtp_password: SMTP password (Gmail App Password).
            dev_mode: If True, simulates sending without actual SMTP.
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.dev_mode = dev_mode
        self.logger = logging.getLogger(__name__)

    def send(
        self, to: str, subject: str, body: str, cc: list[str] | None = None
    ) -> dict[str, Any]:
        """Send an email.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Email body (plain text or HTML).
            cc: CC recipients (optional).

        Returns:
            Dictionary with success status and message_id.
        """
        cc = cc or []

        if self.dev_mode:
            return self._simulate_send(to, subject, body, cc)

        return self._real_send(to, subject, body, cc)

    def _simulate_send(
        self, to: str, subject: str, body: str, cc: list[str]
    ) -> dict[str, Any]:
        """Simulate email sending in DEV_MODE.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Email body.
            cc: CC recipients.

        Returns:
            Simulated send result.
        """
        message_id = f"<simulated-{short_id()}@dev-mode>"

        self.logger.info(
            "[DEV MODE] Simulated email send:\n"
            "  To: %s\n"
            "  CC: %s\n"
            "  Subject: %s\n"
            "  Body: %s",
            to,
            ", ".join(cc) if cc else "None",
            subject,
            body[:100] + "..." if len(body) > 100 else body,
        )

        return {
            "success": True,
            "message_id": message_id,
            "message": "Email simulated in DEV_MODE (not actually sent)",
            "timestamp": now_iso(),
        }

    def _real_send(self, to: str, subject: str, body: str, cc: list[str]) -> dict[str, Any]:
        """Send email via SMTP.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Email body.
            cc: CC recipients.

        Returns:
            Send result with message_id.
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.smtp_user
            msg["To"] = to
            msg["Subject"] = subject

            if cc:
                msg["Cc"] = ", ".join(cc)

            # Attach body (support both plain text and HTML)
            if body.strip().startswith("<"):
                # HTML body
                msg.attach(MIMEText(body, "html"))
            else:
                # Plain text body
                msg.attach(MIMEText(body, "plain"))

            # Connect to SMTP server
            self.logger.info("Connecting to SMTP server: %s:%d", self.smtp_host, self.smtp_port)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)

                # Send email
                recipients = [to] + cc
                server.send_message(msg)

                self.logger.info("Email sent successfully to %s", to)

                # Generate message ID
                message_id = f"<{short_id()}@{self.smtp_host}>"

                return {
                    "success": True,
                    "message_id": message_id,
                    "message": f"Email sent to {to}",
                    "timestamp": now_iso(),
                }

        except smtplib.SMTPAuthenticationError as e:
            self.logger.error("SMTP authentication failed: %s", e)
            return {
                "success": False,
                "error": "Authentication failed. Check SMTP_USER and SMTP_PASSWORD.",
                "details": str(e),
            }

        except smtplib.SMTPException as e:
            self.logger.error("SMTP error: %s", e)
            return {"success": False, "error": "SMTP error", "details": str(e)}

        except Exception as e:
            self.logger.exception("Unexpected error sending email")
            return {"success": False, "error": "Unexpected error", "details": str(e)}
