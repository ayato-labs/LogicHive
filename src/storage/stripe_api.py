import logging
from typing import Any

import stripe

from core.config import get_setting

# Load Stripe Key from Config
STRIPE_API_KEY = get_setting("STRIPE_API_KEY")
stripe.api_key = STRIPE_API_KEY

logger = logging.getLogger(__name__)

# Plan Mapping (Price ID -> Limits)
PLAN_LIMITS = {
    "price_1T5LsGPCeWLY3R8VTNru2yRK": {"limit": 1000, "name": "basic"},
    "price_1T5LsHPCeWLY3R8V9yDLnPMG": {"limit": 10000, "name": "pro"},
}


class StripeBilling:
    """
    Handles B2B Billing via Stripe.
    Connects LogicHive Organizations to Stripe Customers/Subscriptions.
    """

    def __init__(self):
        if not stripe.api_key:
            logger.warning("Stripe: API Key missing. Billing features will be disabled.")

    def create_customer(self, org_name: str, org_id: str) -> str | None:
        """
        Creates a Stripe customer for an organization.
        """
        try:
            customer = stripe.Customer.create(name=org_name, metadata={"org_id": org_id})
            return customer.id
        except Exception as e:
            logger.error(f"Stripe: Failed to create customer: {e}")
            return None

    def get_subscription_status(self, stripe_customer_id: str) -> dict[str, Any]:
        """
        Retrieves active subscription details.
        """
        try:
            subscriptions = stripe.Subscription.list(
                customer=stripe_customer_id, status="active", limit=1
            )
            if subscriptions.data:
                sub = subscriptions.data[0]
                return {
                    "status": sub.status,
                    "plan_id": sub["items"]["data"][0]["price"]["id"],
                    "current_period_end": sub.current_period_end,
                }
            return {"status": "none"}
        except Exception as e:
            logger.error(f"Stripe: Failed to get subscription: {e}")
            return {"status": "error", "message": str(e)}

    def create_checkout_session(
        self,
        stripe_customer_id: str,
        org_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ):
        """
        Generates a Stripe Checkout session for a specific plan tier.
        """
        try:
            session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"org_id": org_id, "price_id": price_id},
            )
            return session.url
        except Exception as e:
            logger.error(f"Stripe: Failed to create checkout session: {e}")
            return None

    def verify_webhook_signature(self, payload: str, sig_header: str, endpoint_secret: str):
        """
        Verifies the Stripe webhook signature.
        """
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
            return event
        except Exception as e:
            logger.error(f"Stripe: Webhook verification failed: {e}")
            return None


# Singleton
stripe_billing = StripeBilling()
