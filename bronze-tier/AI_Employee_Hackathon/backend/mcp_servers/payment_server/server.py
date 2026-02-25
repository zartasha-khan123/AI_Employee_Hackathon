"""Payment Processing MCP Server - secure payment operations.

This MCP server provides tools for processing payments via Stripe with
comprehensive safety controls and HITL approval requirements.

Usage:
    uv run python -m backend.mcp_servers.payment_server.server
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from backend.mcp_servers.payment_server.payment_client import PaymentClient
from backend.mcp_servers.payment_server.safety import (
    PaymentSafetyError,
    check_rate_limit,
    validate_payment_safety,
)
from backend.utils.logging_utils import log_action
from backend.utils.timestamps import now_iso
from backend.utils.uuid_utils import correlation_id

# Configuration
load_dotenv()

DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
VAULT_PATH = os.getenv("VAULT_PATH", "./vault")
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_MODE = os.getenv("STRIPE_MODE", "test")
ALLOWED_PAYMENT_RECIPIENTS = os.getenv("ALLOWED_PAYMENT_RECIPIENTS", "").split(",")
MAX_PAYMENT_AMOUNT = float(os.getenv("MAX_PAYMENT_AMOUNT", "1000.0"))
SECONDARY_APPROVAL_THRESHOLD = float(os.getenv("SECONDARY_APPROVAL_THRESHOLD", "100.0"))

# Logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# MCP Server
mcp = FastMCP(
    "payment-mcp-server",
    instructions=(
        "Payment processing tools with Stripe integration. "
        "ALL payment operations require approval file in vault/Approved/. "
        "Rate limited to 3 transactions per hour, 10 per day. "
        "Maximum single payment: $1000 (configurable)."
    ),
)


@mcp.tool()
async def process_payment(
    amount: float,
    currency: str,
    recipient: str,
    description: str,
) -> str:
    """Process a payment via Stripe.

    ALWAYS requires human approval via vault/Approved/ file.
    NEVER auto-approves payments regardless of amount.

    Args:
        amount: Payment amount (e.g., 100.00 for $100).
        currency: Currency code (USD, EUR, GBP, CAD, AUD).
        recipient: Recipient email or Stripe customer ID.
        description: Clear description of payment purpose (min 5 chars).

    Returns:
        Success message with transaction ID or error message.
    """
    cid = correlation_id()

    # DEV_MODE check
    if DEV_MODE:
        _log_action("process_payment", "simulated", cid, {
            "amount": amount,
            "currency": currency,
            "recipient": recipient,
        })
        return (
            f"[DEV_MODE] Payment processing simulated. "
            f"Amount: {amount} {currency}, Recipient: {recipient}, "
            f"Description: {description[:50]}..."
        )

    # Rate limit check
    try:
        check_rate_limit(VAULT_PATH, limit_per_hour=3, limit_per_day=10)
    except PaymentSafetyError as e:
        _log_action("process_payment", "rate_limited", cid, {"error": str(e)})
        return f"Rate limit exceeded: {e}"

    # Safety validation
    try:
        safety_result = validate_payment_safety(
            amount=amount,
            currency=currency,
            recipient=recipient,
            description=description,
            vault_path=VAULT_PATH,
            allowed_recipients=ALLOWED_PAYMENT_RECIPIENTS if ALLOWED_PAYMENT_RECIPIENTS != [""] else None,
            max_amount=MAX_PAYMENT_AMOUNT,
            secondary_approval_threshold=SECONDARY_APPROVAL_THRESHOLD,
        )

        if not safety_result["safe"]:
            warnings_text = "\n".join(f"  - {w}" for w in safety_result["warnings"])
            return (
                f"Payment safety warnings detected:\n{warnings_text}\n\n"
                f"Review and create approval file if payment is legitimate."
            )

    except PaymentSafetyError as e:
        _log_action("process_payment", "safety_rejected", cid, {"error": str(e)})
        return f"Payment rejected by safety checks: {e}"

    # Check for approval
    approval = _find_approval(
        "payment",
        amount=str(amount),
        recipient=recipient,
    )
    if not approval:
        return (
            "Rejected: No matching approval file found in vault/Approved/ "
            "for payment. Create approval file with type: payment, "
            f"amount: {amount}, recipient: {recipient}"
        )

    # Check Stripe configuration
    if not STRIPE_API_KEY:
        return "Error: Stripe not configured. Set STRIPE_API_KEY in .env"

    # Process payment
    try:
        client = PaymentClient(STRIPE_API_KEY, mode=STRIPE_MODE)
        result = client.process_payment(
            amount=amount,
            currency=currency,
            recipient=recipient,
            description=description,
            metadata={
                "correlation_id": cid,
                "approved_by": approval.get("approved_by", "human"),
            }
        )

        # Consume approval
        _consume_approval(approval["path"])

        _log_action("process_payment", "success", cid, {
            "transaction_id": result["transaction_id"],
            "amount": amount,
            "currency": currency,
            "recipient": recipient,
        })

        return (
            f"Payment processed successfully.\n"
            f"Transaction ID: {result['transaction_id']}\n"
            f"Amount: {amount} {currency}\n"
            f"Recipient: {recipient}\n"
            f"Status: {result['status']}"
        )

    except Exception as e:
        logger.exception("Failed to process payment")
        _log_action("process_payment", "error", cid, {"error": str(e)})
        return f"Error processing payment: {e}"


@mcp.tool()
async def refund_payment(
    transaction_id: str,
    amount: float | None = None,
    reason: str | None = None,
) -> str:
    """Refund a payment.

    Requires human approval via vault/Approved/ file.

    Args:
        transaction_id: Original payment transaction ID.
        amount: Refund amount (None for full refund).
        reason: Reason for refund.

    Returns:
        Success message with refund ID or error message.
    """
    cid = correlation_id()

    # DEV_MODE check
    if DEV_MODE:
        _log_action("refund_payment", "simulated", cid, {
            "transaction_id": transaction_id,
            "amount": amount,
        })
        return (
            f"[DEV_MODE] Refund simulated. "
            f"Transaction: {transaction_id}, Amount: {amount or 'full'}"
        )

    # Check for approval
    approval = _find_approval(
        "payment_refund",
        transaction_id=transaction_id,
    )
    if not approval:
        return (
            "Rejected: No matching approval file found in vault/Approved/ "
            "for refund. Create approval file with type: payment_refund, "
            f"transaction_id: {transaction_id}"
        )

    # Check Stripe configuration
    if not STRIPE_API_KEY:
        return "Error: Stripe not configured. Set STRIPE_API_KEY in .env"

    # Process refund
    try:
        client = PaymentClient(STRIPE_API_KEY, mode=STRIPE_MODE)
        result = client.refund_payment(
            transaction_id=transaction_id,
            amount=amount,
            reason=reason,
        )

        # Consume approval
        _consume_approval(approval["path"])

        _log_action("refund_payment", "success", cid, {
            "refund_id": result["refund_id"],
            "transaction_id": transaction_id,
            "amount": result.get("amount"),
        })

        return (
            f"Refund processed successfully.\n"
            f"Refund ID: {result['refund_id']}\n"
            f"Transaction ID: {transaction_id}\n"
            f"Amount: {result.get('amount', 'full')}\n"
            f"Status: {result['status']}"
        )

    except Exception as e:
        logger.exception("Failed to process refund")
        _log_action("refund_payment", "error", cid, {"error": str(e)})
        return f"Error processing refund: {e}"


@mcp.tool()
async def check_payment_status(transaction_id: str) -> str:
    """Check the status of a payment.

    Does not require approval (read-only operation).

    Args:
        transaction_id: Payment transaction ID to check.

    Returns:
        Payment status information or error message.
    """
    cid = correlation_id()

    # DEV_MODE check
    if DEV_MODE:
        _log_action("check_payment_status", "simulated", cid, {
            "transaction_id": transaction_id,
        })
        return (
            f"[DEV_MODE] Payment status check simulated. "
            f"Transaction: {transaction_id}"
        )

    # Check Stripe configuration
    if not STRIPE_API_KEY:
        return "Error: Stripe not configured. Set STRIPE_API_KEY in .env"

    # Check status
    try:
        client = PaymentClient(STRIPE_API_KEY, mode=STRIPE_MODE)
        result = client.check_payment_status(transaction_id)

        _log_action("check_payment_status", "success", cid, {
            "transaction_id": transaction_id,
            "status": result["status"],
        })

        return (
            f"Payment Status:\n"
            f"Transaction ID: {result['transaction_id']}\n"
            f"Status: {result['status']}\n"
            f"Amount: {result['amount']} {result['currency']}\n"
            f"Created: {result['created']}"
        )

    except Exception as e:
        logger.exception("Failed to check payment status")
        _log_action("check_payment_status", "error", cid, {"error": str(e)})
        return f"Error checking payment status: {e}"


def _find_approval(action_type: str, **kwargs) -> dict[str, Any] | None:
    """Find matching approval file in vault/Approved/."""
    approved_dir = Path(VAULT_PATH) / "Approved"
    if not approved_dir.exists():
        return None

    for file_path in approved_dir.glob("*.md"):
        try:
            from backend.utils.frontmatter import extract_frontmatter

            content = file_path.read_text(encoding="utf-8")
            frontmatter, _ = extract_frontmatter(content)

            if frontmatter.get("type") == action_type:
                # Check if kwargs match
                match = all(
                    str(frontmatter.get(k, "")).lower() == str(v).lower()
                    for k, v in kwargs.items()
                )
                if match:
                    return {"path": str(file_path), "type": action_type}
        except Exception:
            continue

    return None


def _consume_approval(approval_path: str) -> None:
    """Move approval file to Done/ after execution."""
    from shutil import move

    approval_file = Path(approval_path)
    done_dir = Path(VAULT_PATH) / "Done"
    done_dir.mkdir(exist_ok=True)

    # Update frontmatter
    from backend.utils.frontmatter import update_frontmatter

    update_frontmatter(approval_file, {"status": "done", "completed_at": now_iso()})

    # Move to Done
    dest = done_dir / approval_file.name
    move(str(approval_file), str(dest))


def _log_action(action_type: str, result: str, cid: str, params: dict[str, Any] | None = None) -> None:
    """Log action to vault/Logs/actions/."""
    log_dir = Path(VAULT_PATH) / "Logs" / "actions"
    try:
        log_action(
            log_dir,
            {
                "timestamp": now_iso(),
                "correlation_id": cid,
                "actor": "payment_mcp",
                "action_type": action_type,
                "target": "stripe_payment",
                "result": result,
                "parameters": params or {},
            },
        )
    except OSError:
        logger.exception("Failed to write audit log")


def main() -> None:
    """CLI entry point for the Payment MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
