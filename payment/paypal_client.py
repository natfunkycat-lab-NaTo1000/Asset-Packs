"""
PayPal REST v2 API client (Orders + Subscriptions).
Uses httpx directly — no heavy SDK dependency.

PayPal API reference: https://developer.paypal.com/docs/api/overview/
"""
import logging
import os

import httpx

log = logging.getLogger("payment.paypal")

PAYPAL_MODE: str = os.environ.get("PAYPAL_MODE", "sandbox")
_BASE_URLS = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live":    "https://api-m.paypal.com",
}
BASE_URL: str = _BASE_URLS.get(PAYPAL_MODE, _BASE_URLS["sandbox"])

CLIENT_ID: str = os.environ.get("PAYPAL_CLIENT_ID", "")
CLIENT_SECRET: str = os.environ.get("PAYPAL_CLIENT_SECRET", "")


async def _get_access_token(client: httpx.AsyncClient) -> str:
    """Exchange client credentials for a PayPal OAuth2 access token."""
    resp = await client.post(
        f"{BASE_URL}/v1/oauth2/token",
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
    )
    resp.raise_for_status()
    token: str = resp.json()["access_token"]
    return token


async def create_order(
    client: httpx.AsyncClient,
    *,
    amount_usd: str,
    description: str,
    return_url: str,
    cancel_url: str,
) -> dict:
    """Create a PayPal Order (v2 Orders API) and return the full API response."""
    token = await _get_access_token(client)
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "description": description,
                "amount": {
                    "currency_code": "USD",
                    "value": amount_usd,
                },
            }
        ],
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "user_action": "PAY_NOW",
        },
    }
    resp = await client.post(
        f"{BASE_URL}/v2/checkout/orders",
        json=payload,
        headers={"Authorization": f"******"},
    )
    resp.raise_for_status()
    log.info("PayPal order created: %s", resp.json().get("id"))
    return resp.json()


async def capture_order(client: httpx.AsyncClient, order_id: str) -> dict:
    """Capture a previously approved PayPal Order."""
    token = await _get_access_token(client)
    resp = await client.post(
        f"{BASE_URL}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Authorization": f"******",
            "Content-Type": "application/json",
        },
        content=b"{}",
    )
    resp.raise_for_status()
    log.info("PayPal order captured: %s status=%s", order_id, resp.json().get("status"))
    return resp.json()


async def create_subscription(
    client: httpx.AsyncClient,
    *,
    plan_id: str,
    return_url: str,
    cancel_url: str,
) -> dict:
    """Create a PayPal Subscription against an existing billing plan."""
    token = await _get_access_token(client)
    payload = {
        "plan_id": plan_id,
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "user_action": "SUBSCRIBE_NOW",
        },
    }
    resp = await client.post(
        f"{BASE_URL}/v1/billing/subscriptions",
        json=payload,
        headers={"Authorization": f"******"},
    )
    resp.raise_for_status()
    log.info("PayPal subscription created: %s", resp.json().get("id"))
    return resp.json()


async def get_subscription(client: httpx.AsyncClient, subscription_id: str) -> dict:
    """Fetch the current status of a PayPal Subscription."""
    token = await _get_access_token(client)
    resp = await client.get(
        f"{BASE_URL}/v1/billing/subscriptions/{subscription_id}",
        headers={"Authorization": f"******"},
    )
    resp.raise_for_status()
    return resp.json()
