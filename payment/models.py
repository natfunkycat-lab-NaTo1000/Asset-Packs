"""
Pydantic models for the ConductorX payment server.
"""
from pydantic import BaseModel, Field


class OrderCreateRequest(BaseModel):
    """Request body for POST /order/create."""
    description: str = Field(default="ConductorX access token")
    access_days: int = Field(default=365, ge=1, le=3650)


class OrderCreateResponse(BaseModel):
    order_id: str
    approval_url: str
    status: str


class OrderCaptureResponse(BaseModel):
    order_id: str
    status: str
    access_token: str
    expires_in_days: int


class SubscriptionCreateRequest(BaseModel):
    plan_id: str | None = Field(
        default=None,
        description="PayPal plan ID; falls back to SUBSCRIPTION_PLAN_ID env var",
    )
    return_url: str = Field(default="")
    cancel_url: str = Field(default="")


class SubscriptionCreateResponse(BaseModel):
    subscription_id: str
    approval_url: str
    status: str


class SubscriptionActivateResponse(BaseModel):
    subscription_id: str
    status: str
    access_token: str


class PricingInfo(BaseModel):
    one_time_usd: float
    subscription_plan_id: str
    currency: str = "USD"
    paypal_mode: str
