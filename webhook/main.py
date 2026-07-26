#!/usr/bin/env python3
"""
ConductorX Webhook Server (Component 4)
FastAPI app that receives GitHub webhook events and dispatches
Celery tasks to the worker mesh.
"""
import hashlib
import hmac
import os

from fastapi import FastAPI, Header, HTTPException, Request
from workers.celery_app import check_pack, generate_previews, reindex, repack_pack

WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

app = FastAPI(title="ConductorX Webhook", version="1.0.0")


def _verify_signature(payload: bytes, sig_header: str) -> None:
    """Validate the GitHub webhook HMAC-SHA256 signature."""
    if not WEBHOOK_SECRET:
        return  # skip validation if secret not configured (dev mode)
    if not sig_header or not sig_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Missing or malformed signature")
    expected = "sha256=" + hmac.HMAC(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig_header):
        raise HTTPException(status_code=401, detail="Invalid signature")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str = Header(default=""),
) -> dict:
    """Receive a GitHub webhook event and dispatch the appropriate task."""
    payload = await request.body()
    _verify_signature(payload, x_hub_signature_256)

    data = await request.json()

    if x_github_event == "push":
        ref = data.get("ref", "")
        if ref == "refs/heads/dev":
            # Repack all packs and trigger reindex on push to dev
            repack_pack.delay(pack_name=None)
            reindex.delay()
            return {"dispatched": ["repack_pack", "reindex"]}

    if x_github_event == "pull_request":
        action = data.get("action", "")
        if action in ("opened", "synchronize"):
            check_pack.delay(pack_name=None)
            return {"dispatched": ["check_pack"]}

    if x_github_event == "release":
        action = data.get("action", "")
        if action == "published":
            repack_pack.delay(pack_name=None)
            generate_previews.delay(pack_name=None)
            reindex.delay()
            return {"dispatched": ["repack_pack", "generate_previews", "reindex"]}

    return {"dispatched": []}


@app.post("/trigger/repack")
async def trigger_repack(pack_name: str | None = None) -> dict:
    """Manually trigger a repack (for mobile/tablet use)."""
    task = repack_pack.delay(pack_name=pack_name)
    return {"task_id": task.id, "pack_name": pack_name}


@app.post("/trigger/check")
async def trigger_check(pack_name: str | None = None) -> dict:
    """Manually trigger a format check."""
    task = check_pack.delay(pack_name=pack_name)
    return {"task_id": task.id, "pack_name": pack_name}


@app.post("/trigger/previews")
async def trigger_previews(pack_name: str | None = None) -> dict:
    """Manually trigger preview generation."""
    task = generate_previews.delay(pack_name=pack_name)
    return {"task_id": task.id, "pack_name": pack_name}


@app.post("/trigger/reindex")
async def trigger_reindex() -> dict:
    """Manually trigger reindex."""
    task = reindex.delay()
    return {"task_id": task.id}
