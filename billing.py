"""Stripe billing integration.

Setup:
1. Create Stripe account at https://stripe.com
2. Get API keys from Dashboard → Developers → API keys
3. Set env vars: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
4. Create products in Stripe Dashboard matching PLANS in auth.py
"""
import os
from typing import Optional

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# Stripe Price IDs - create these in your Stripe Dashboard
# and set as env vars, or hardcode after creation
PRICE_IDS = {
    "pay_per": os.environ.get("STRIPE_PRICE_PAY_PER", ""),   # $29 for 10 revisions
    "pro": os.environ.get("STRIPE_PRICE_PRO", ""),           # $99/month unlimited
}


def _stripe():
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


def create_checkout_session(user_id: str, email: str, plan: str,
                            success_url: str, cancel_url: str) -> str:
    """
    Create a Stripe Checkout session. Returns the checkout URL.
    User completes payment on Stripe's hosted page.
    """
    stripe = _stripe()
    price_id = PRICE_IDS.get(plan)
    if not price_id:
        raise ValueError(f"No Stripe price configured for plan: {plan}")

    mode = "subscription" if plan == "pro" else "payment"
    session = stripe.checkout.Session.create(
        customer_email=email,
        line_items=[{"price": price_id, "quantity": 1}],
        mode=mode,
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"user_id": user_id, "plan": plan},
    )
    return session.url


def handle_webhook(payload: bytes, sig_header: str) -> Optional[dict]:
    """
    Verify and process Stripe webhook.
    Returns {"user_id": ..., "plan": ...} on successful payment.
    """
    stripe = _stripe()
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise ValueError(f"Webhook verification failed: {e}")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        return {
            "user_id": session["metadata"].get("user_id"),
            "plan": session["metadata"].get("plan"),
            "stripe_customer_id": session.get("customer"),
            "session_id": session["id"],
        }
    return None


def is_configured() -> bool:
    return bool(STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET)
