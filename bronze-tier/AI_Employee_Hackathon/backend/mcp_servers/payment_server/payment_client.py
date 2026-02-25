"""Payment processing client for Stripe integration."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PaymentClient:
    """Client for processing payments via Stripe."""

    def __init__(self, api_key: str, mode: str = "test"):
        """Initialize payment client.

        Args:
            api_key: Stripe API key (test or live)
            mode: 'test' or 'live' mode
        """
        self.api_key = api_key
        self.mode = mode
        self._stripe = None

    def _init_stripe(self):
        """Lazy initialization of Stripe SDK."""
        if self._stripe is None:
            try:
                import stripe
                self._stripe = stripe
                self._stripe.api_key = self.api_key
            except ImportError:
                raise Exception(
                    "Stripe SDK not installed. Run: uv pip install stripe"
                )

    def process_payment(
        self,
        amount: float,
        currency: str,
        recipient: str,
        description: str,
        metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Process a payment.

        Args:
            amount: Payment amount (in currency units, e.g., 100.00 for $100)
            currency: Currency code (e.g., 'usd', 'eur')
            recipient: Recipient identifier (email or Stripe customer ID)
            description: Payment description
            metadata: Additional metadata

        Returns:
            Payment result with transaction ID and status

        Raises:
            Exception: If payment fails
        """
        self._init_stripe()

        try:
            # Convert amount to cents for Stripe
            amount_cents = int(amount * 100)

            # Create payment intent
            payment_intent = self._stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                description=description,
                metadata=metadata or {},
                receipt_email=recipient if "@" in recipient else None,
            )

            logger.info(
                f"Payment processed: {payment_intent.id} "
                f"({amount} {currency.upper()} to {recipient})"
            )

            return {
                "transaction_id": payment_intent.id,
                "status": payment_intent.status,
                "amount": amount,
                "currency": currency.upper(),
                "recipient": recipient,
                "description": description,
            }

        except Exception as e:
            logger.exception("Payment processing failed")
            raise Exception(f"Payment failed: {e}")

    def refund_payment(
        self,
        transaction_id: str,
        amount: float | None = None,
        reason: str | None = None
    ) -> dict[str, Any]:
        """Refund a payment.

        Args:
            transaction_id: Original payment intent ID
            amount: Refund amount (None for full refund)
            reason: Refund reason

        Returns:
            Refund result

        Raises:
            Exception: If refund fails
        """
        self._init_stripe()

        try:
            refund_params = {"payment_intent": transaction_id}

            if amount is not None:
                refund_params["amount"] = int(amount * 100)

            if reason:
                refund_params["reason"] = reason

            refund = self._stripe.Refund.create(**refund_params)

            logger.info(f"Refund processed: {refund.id} for {transaction_id}")

            return {
                "refund_id": refund.id,
                "status": refund.status,
                "amount": refund.amount / 100 if refund.amount else None,
                "transaction_id": transaction_id,
            }

        except Exception as e:
            logger.exception("Refund processing failed")
            raise Exception(f"Refund failed: {e}")

    def check_payment_status(self, transaction_id: str) -> dict[str, Any]:
        """Check payment status.

        Args:
            transaction_id: Payment intent ID

        Returns:
            Payment status information

        Raises:
            Exception: If status check fails
        """
        self._init_stripe()

        try:
            payment_intent = self._stripe.PaymentIntent.retrieve(transaction_id)

            return {
                "transaction_id": payment_intent.id,
                "status": payment_intent.status,
                "amount": payment_intent.amount / 100,
                "currency": payment_intent.currency.upper(),
                "created": payment_intent.created,
            }

        except Exception as e:
            logger.exception("Payment status check failed")
            raise Exception(f"Status check failed: {e}")
