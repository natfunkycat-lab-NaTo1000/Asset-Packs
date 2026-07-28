#!/usr/bin/env python3
"""
ConductorX Payment Server
FastAPI app that presents a PayPal payment wall and issues signed JWTs after
successful payment.  The JWTs are validated by the webhook server before
allowing access to the manual /trigger/* endpoints.

Endpoints:
  GET  /                               — pricing information
  POST /order/create                   — create a PayPal Order
  GET  /order/capture                  — capture order after PayPal redirect
  POST /subscription/create            — create a PayPal subscription
  GET  /subscription/activate          — activate subscription after PayPal redirect
  GET  /health                         — health check
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import FastAPI, HTTPException, Query, status
from jose import jwt

from payment import paypal_client
from payment.models import (
    OrderCaptureResponse,
    OrderCreateRequest,
    OrderCreateResponse,
    PricingInfo,
    SubscriptionActivateResponse,
    SubscriptionCreateRequest,
    SubscriptionCreateResponse,
)

# ── configuration ──────────────────────────────────────────────────────────────
JWT_SECRET: str = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM: str = "HS256"
JWT_DEFAULT_DAYS: int = int(os.environ.get("JWT_ACCESS_DAYS", "365"))
PRICE_USD: str = os.environ.get("PRICE_USD", "9.99")
SUBSCRIPTION_PLAN_ID: str = os.environ.get("SUBSCRIPTION_PLAN_ID", "")
DOMAIN: str = os.environ.get("DOMAIN", "localhost:8001")
PAYPAL_MODE: str = os.environ.get("PAYPAL_MODE", "sandbox")

log = logging.getLogger("payment")
logging.basicConfig(level=logging.INFO)

_http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http_client
    _http_client = httpx.AsyncClient(timeout=30.0)
    yield
    await _http_client.aclose()


app = FastAPI(
    title="ConductorX Payment Server",
    version="1.0.0",
    description=(
        "PayPal payment wall for ConductorX. "
        "Successful payment issues a JWT for authenticated access to the "
        "webhook server's manual trigger endpoints."
    ),
    lifespan=lifespan,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _issue_jwt(subject: str, days: int = JWT_DEFAULT_DAYS) -> str:
    """Sign and return a JWT granting access for the given number of days."""
    if not JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET is not configured on this server",
        )
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(days=days),
        "scope": "trigger",
    }
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _return_url(path: str) -> str:
    scheme = "http" if "localhost" in DOMAIN else "https"
    return f"{scheme}://{DOMAIN}{path}"


def _require_client() -> httpx.AsyncClient:
    if _http_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HTTP client not initialised",
        )
    return _http_client


# ── routes ─────────────────────────────────────────────────────────────────────

@app.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok", "paypal_mode": PAYPAL_MODE}


@app.get("/", summary="Pricing information", response_model=PricingInfo)
async def pricing() -> PricingInfo:
    """Return current pricing for the ConductorX access token."""
    return PricingInfo(
        one_time_usd=float(PRICE_USD),
        subscription_plan_id=SUBSCRIPTION_PLAN_ID,
        paypal_mode=PAYPAL_MODE,
    )


@app.post(
    "/order/create",
    summary="Create a PayPal Order",
    response_model=OrderCreateResponse,
)
async def order_create(body: OrderCreateRequest) -> OrderCreateResponse:
    """
    Create a PayPal Order for the one-time purchase price.
    Returns the PayPal approval URL — redirect the user there to pay.
    """
    client = _require_client()
    try:
        data = await paypal_client.create_order(
            client,
            amount_usd=PRICE_USD,
            description=body.description,
            return_url=_return_url(f"/order/capture?access_days={body.access_days}"),
            cancel_url=_return_url("/order/cancel"),
        )
    except httpx.HTTPStatusError as exc:
        log.error("PayPal order creation failed: %s", exc.response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="PayPal order creation failed",
        ) from exc

    approval_url = next(
        (link["href"] for link in data.get("links", []) if link.get("rel") == "approve"),
        "",
    )
    return OrderCreateResponse(
        order_id=data["id"],
        approval_url=approval_url,
        status=data.get("status", ""),
    )


@app.get(
    "/order/capture",
    summary="Capture a PayPal Order (redirect callback)",
    response_model=OrderCaptureResponse,
)
async def order_capture(
    token: str = Query(..., description="PayPal order token from redirect"),
    access_days: int = Query(default=JWT_DEFAULT_DAYS, ge=1),
) -> OrderCaptureResponse:
    """
    Called by PayPal after the user approves the payment.
    Captures the order and issues a signed JWT.
    """
    client = _require_client()
    try:
        data = await paypal_client.capture_order(client, token)
    except httpx.HTTPStatusError as exc:
        log.error("PayPal capture failed for order %s: %s", token, exc.response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="PayPal payment capture failed",
        ) from exc

    pp_status = data.get("status", "")
    if pp_status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment not completed (status: {pp_status})",
        )

    payer_email = (
        data.get("payment_source", {})
        .get("paypal", {})
        .get("email_address", token)
    )
    access_token = _issue_jwt(subject=payer_email, days=access_days)
    return OrderCaptureResponse(
        order_id=token,
        status=pp_status,
        access_token=access_token,
        expires_in_days=access_days,
    )


@app.get("/order/cancel", summary="Order cancelled by user")
async def order_cancel() -> dict:
    return {"status": "cancelled", "message": "Payment was cancelled. No charge was made."}


@app.post(
    "/subscription/create",
    summary="Create a PayPal Subscription",
    response_model=SubscriptionCreateResponse,
)
async def subscription_create(body: SubscriptionCreateRequest) -> SubscriptionCreateResponse:
    """
    Create a recurring PayPal Subscription.
    Returns the PayPal approval URL — redirect the user there to subscribe.
    """
    plan_id = body.plan_id or SUBSCRIPTION_PLAN_ID
    if not plan_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="plan_id is required (or set SUBSCRIPTION_PLAN_ID env var)",
        )
    client = _require_client()
    try:
        data = await paypal_client.create_subscription(
            client,
            plan_id=plan_id,
            return_url=body.return_url or _return_url("/subscription/activate"),
            cancel_url=body.cancel_url or _return_url("/subscription/cancel"),
        )
    except httpx.HTTPStatusError as exc:
        log.error("PayPal subscription creation failed: %s", exc.response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="PayPal subscription creation failed",
        ) from exc

    approval_url = next(
        (link["href"] for link in data.get("links", []) if link.get("rel") == "approve"),
        "",
    )
    return SubscriptionCreateResponse(
        subscription_id=data["id"],
        approval_url=approval_url,
        status=data.get("status", ""),
    )


@app.get(
    "/subscription/activate",
    summary="Activate a PayPal Subscription (redirect callback)",
    response_model=SubscriptionActivateResponse,
)
async def subscription_activate(
    subscription_id: str = Query(...),
) -> SubscriptionActivateResponse:
    """
    Called by PayPal after the user approves a subscription.
    Verifies the subscription is active and issues a signed JWT.
    """
    client = _require_client()
    try:
        data = await paypal_client.get_subscription(client, subscription_id)
    except httpx.HTTPStatusError as exc:
        log.error("PayPal subscription fetch failed: %s", exc.response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify subscription with PayPal",
        ) from exc

    pp_status = data.get("status", "")
    if pp_status not in ("ACTIVE", "APPROVED"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Subscription not active (status: {pp_status})",
        )

    subscriber_email = (
        data.get("subscriber", {}).get("email_address", subscription_id)
    )
    access_token = _issue_jwt(subject=subscriber_email, days=36500)  # ~100 years, subscription managed by PayPal
    return SubscriptionActivateResponse(
        subscription_id=subscription_id,
        status=pp_status,
        access_token=access_token,
    )


@app.get("/subscription/cancel", summary="Subscription cancelled by user")
async def subscription_cancel() -> dict:
    return {"status": "cancelled", "message": "Subscription was cancelled. No charge was made."}
