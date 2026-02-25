"""Odoo MCP Server - integrates with Odoo ERP for invoicing and CRM.

This MCP server provides tools for interacting with Odoo via XML-RPC API.

Usage:
    uv run python -m backend.mcp_servers.odoo_server.server
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from backend.mcp_servers.odoo_server.odoo_client import OdooClient
from backend.utils.logging_utils import log_action
from backend.utils.timestamps import now_iso
from backend.utils.uuid_utils import correlation_id

# Configuration
load_dotenv()

DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
VAULT_PATH = os.getenv("VAULT_PATH", "./vault")
ODOO_URL = os.getenv("ODOO_URL", "")
ODOO_DATABASE = os.getenv("ODOO_DATABASE", "")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "")
ODOO_API_KEY = os.getenv("ODOO_API_KEY", "")

# Logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# MCP Server
mcp = FastMCP(
    "odoo-mcp-server",
    instructions=(
        "Odoo ERP tools for invoicing and CRM. "
        "All invoice creation requires approval file in vault/Approved/. "
        "Rate limited to 20 requests per hour."
    ),
)


@mcp.tool()
async def create_invoice(
    partner_name: str,
    line_items: str,
    due_date: str | None = None
) -> str:
    """Create an invoice in Odoo.

    ALWAYS requires human approval via vault/Approved/ file.

    Args:
        partner_name: Customer/partner name.
        line_items: JSON string of line items with description, quantity, price.
        due_date: Invoice due date (YYYY-MM-DD format).

    Returns:
        Success message with invoice ID or error message.
    """
    cid = correlation_id()

    # DEV_MODE check
    if DEV_MODE:
        _log_action("create_invoice", "simulated", cid, {"partner": partner_name})
        return (
            f"[DEV_MODE] Invoice creation simulated. "
            f"Partner: {partner_name}, Items: {line_items[:50]}..."
        )

    # Check for approval
    approval = _find_approval("odoo_invoice", partner=partner_name)
    if not approval:
        return (
            "Rejected: No matching approval file found in vault/Approved/ "
            "for Odoo invoice. Create approval file with type: odoo_invoice"
        )

    # Check Odoo configuration
    if not all([ODOO_URL, ODOO_DATABASE, ODOO_USERNAME, ODOO_API_KEY]):
        return "Error: Odoo not configured. Set ODOO_URL, ODOO_DATABASE, ODOO_USERNAME, ODOO_API_KEY in .env"

    # Create invoice
    try:
        client = OdooClient(ODOO_URL, ODOO_DATABASE, ODOO_USERNAME, ODOO_API_KEY)
        invoice_id = client.create_invoice(partner_name, line_items, due_date)

        # Consume approval
        _consume_approval(approval["path"])

        _log_action("create_invoice", "success", cid, {
            "partner": partner_name,
            "invoice_id": invoice_id
        })
        return f"Invoice created successfully. Odoo Invoice ID: {invoice_id}"

    except Exception as e:
        logger.exception("Failed to create Odoo invoice")
        _log_action("create_invoice", "error", cid, {"error": str(e)})
        return f"Error creating invoice: {e}"


@mcp.tool()
async def search_partner(name: str) -> str:
    """Search for a partner/customer in Odoo.

    Args:
        name: Partner name to search for.

    Returns:
        Partner information or error message.
    """
    cid = correlation_id()

    # DEV_MODE check
    if DEV_MODE:
        _log_action("search_partner", "simulated", cid, {"name": name})
        return f"[DEV_MODE] Partner search simulated. Query: {name}"

    # Check Odoo configuration
    if not all([ODOO_URL, ODOO_DATABASE, ODOO_USERNAME, ODOO_API_KEY]):
        return "Error: Odoo not configured"

    try:
        client = OdooClient(ODOO_URL, ODOO_DATABASE, ODOO_USERNAME, ODOO_API_KEY)
        partners = client.search_partner(name)

        _log_action("search_partner", "success", cid, {"count": len(partners)})

        if not partners:
            return f"No partners found matching: {name}"

        result = f"Found {len(partners)} partner(s):\n"
        for p in partners[:5]:  # Limit to 5 results
            result += f"- {p['name']} (ID: {p['id']})\n"

        return result

    except Exception as e:
        logger.exception("Failed to search Odoo partners")
        _log_action("search_partner", "error", cid, {"error": str(e)})
        return f"Error searching partners: {e}"


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
                "actor": "odoo_mcp",
                "action_type": action_type,
                "target": "odoo_erp",
                "result": result,
                "parameters": params or {},
            },
        )
    except OSError:
        logger.exception("Failed to write audit log")


def main() -> None:
    """CLI entry point for the Odoo MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
