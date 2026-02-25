"""Odoo XML-RPC client for ERP integration."""

from __future__ import annotations

import json
import logging
import xmlrpc.client
from typing import Any

logger = logging.getLogger(__name__)


class OdooClient:
    """Client for interacting with Odoo via XML-RPC."""

    def __init__(self, url: str, database: str, username: str, api_key: str):
        """Initialize Odoo client.

        Args:
            url: Odoo instance URL (e.g., https://your-instance.odoo.com)
            database: Database name
            username: Username (email)
            api_key: API key or password
        """
        self.url = url.rstrip("/")
        self.database = database
        self.username = username
        self.api_key = api_key

        # XML-RPC endpoints
        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

        self.uid: int | None = None

    def authenticate(self) -> int:
        """Authenticate with Odoo and get user ID.

        Returns:
            User ID.

        Raises:
            Exception: If authentication fails.
        """
        if self.uid:
            return self.uid

        try:
            self.uid = self.common.authenticate(
                self.database,
                self.username,
                self.api_key,
                {}
            )

            if not self.uid:
                raise Exception("Authentication failed: Invalid credentials")

            logger.info(f"Authenticated with Odoo as user ID: {self.uid}")
            return self.uid

        except Exception as e:
            logger.exception("Odoo authentication failed")
            raise Exception(f"Odoo authentication failed: {e}")

    def create_invoice(
        self,
        partner_name: str,
        line_items: str,
        due_date: str | None = None
    ) -> int:
        """Create an invoice in Odoo.

        Args:
            partner_name: Customer/partner name
            line_items: JSON string of line items
            due_date: Invoice due date (YYYY-MM-DD)

        Returns:
            Invoice ID

        Raises:
            Exception: If invoice creation fails
        """
        self.authenticate()

        # Parse line items
        try:
            items = json.loads(line_items)
        except json.JSONDecodeError:
            raise Exception("Invalid line_items JSON format")

        # Search for partner
        partner_ids = self.models.execute_kw(
            self.database,
            self.uid,
            self.api_key,
            "res.partner",
            "search",
            [[["name", "ilike", partner_name]]],
            {"limit": 1}
        )

        if not partner_ids:
            raise Exception(f"Partner not found: {partner_name}")

        partner_id = partner_ids[0]

        # Prepare invoice lines
        invoice_lines = []
        for item in items:
            invoice_lines.append((0, 0, {
                "name": item.get("description", ""),
                "quantity": item.get("quantity", 1),
                "price_unit": item.get("price", 0.0),
            }))

        # Create invoice
        invoice_data = {
            "partner_id": partner_id,
            "move_type": "out_invoice",
            "invoice_line_ids": invoice_lines,
        }

        if due_date:
            invoice_data["invoice_date_due"] = due_date

        invoice_id = self.models.execute_kw(
            self.database,
            self.uid,
            self.api_key,
            "account.move",
            "create",
            [invoice_data]
        )

        logger.info(f"Created Odoo invoice ID: {invoice_id}")
        return invoice_id

    def search_partner(self, name: str) -> list[dict[str, Any]]:
        """Search for partners by name.

        Args:
            name: Partner name to search

        Returns:
            List of partner dictionaries

        Raises:
            Exception: If search fails
        """
        self.authenticate()

        partner_ids = self.models.execute_kw(
            self.database,
            self.uid,
            self.api_key,
            "res.partner",
            "search",
            [[["name", "ilike", name]]],
            {"limit": 10}
        )

        if not partner_ids:
            return []

        partners = self.models.execute_kw(
            self.database,
            self.uid,
            self.api_key,
            "res.partner",
            "read",
            [partner_ids],
            {"fields": ["id", "name", "email", "phone"]}
        )

        return partners
