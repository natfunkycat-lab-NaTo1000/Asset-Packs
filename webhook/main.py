#!/usr/bin/env python3
"""
ConductorX Webhook Server (Component 4) — v2
FastAPI app that receives GitHub webhook events, validates HMAC-SHA256
signatures, dispatches Celery tasks to the worker mesh, and forwards
notifications to each stage of the iNFINITEAi2025 quad pipeline on HuggingFace
(https://huggingface.co/NaTo1000/iNFINITEAi2025).
"""
import hashlib
import hmac
import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, status

from workers.celery_app import check_pack, generate_previews, reindex, repack_pack

# ── configuration ──────────────────────────────────────────────────────────────
WEBHOOK_SECRET: str = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
HF_API_TOKEN: str = os.environ.get("HF_API_TOKEN", "")
HF_PIPELINE_URL: str = os.environ.get(
    "HF_PIPELINE_URL",
    "https://huggingface.co/NaTo1000/iNFINITEAi2025",
)

# The quad pipeline has four stages matching the four ConductorX tasks.
HF_QUAD_ENDPOINTS: dict[str, str] = {
    "check":    f"{HF_PIPELINE_URL}/resolve/main/check",
    "repack":   f"{HF_PIPELINE_URL}/resolve/main/repack",
    "previews": f"{HF_PIPELINE_URL}/resolve/main/previews",
    "reindex":  f"{HF_PIPELINE_URL}/resolve/main/reindex",
}

log = logging.getLogger("webhook")
logging.basicConfig(level=logging.INFO)

# ── shared async HTTP client ───────────────────────────────────────────────────
_http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http_client
    headers = {"Authorization": f"******"} if HF_API_TOKEN else {}
    _http_client = httpx.AsyncClient(headers=headers, timeout=30.0)
    yield
    await _http_client.aclose()


app = FastAPI(
    title="ConductorX Webhook",
    version="2.0.0",
    description=(
        "GitHub webhook receiver for the ConductorX pipeline. "
        "Dispatches tasks to the Celery worker mesh and the "
        "[iNFINITEAi2025 quad pipeline](https://huggingface.co/NaTo1000/iNFINITEAi2025) "
        "on HuggingFace."
    ),
    lifespan=lifespan,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _verify_signature(payload: bytes, sig_header: str) -> None:
    """Validate the GitHub webhook HMAC-SHA256 signature."""
    if not WEBHOOK_SECRET:
        return  # skip in dev / test mode when secret is not configured
    if not sig_header or not sig_header.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed X-Hub-Signature-256 header",
        )
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature mismatch — verify GITHUB_WEBHOOK_SECRET matches the webhook secret",
        )


async def _notify_hf_pipeline(stage: str, payload: dict) -> None:
    """Forward an event notification to the matching quad-pipeline stage on HuggingFace."""
    if _http_client is None or stage not in HF_QUAD_ENDPOINTS:
        return
    url = HF_QUAD_ENDPOINTS[stage]
    try:
        resp = await _http_client.post(url, json=payload)
        resp.raise_for_status()
        log.info("HF pipeline [%s] notified → %s %s", stage, resp.status_code, url)
    except httpx.HTTPError as exc:
        log.warning("HF pipeline notification failed for stage [%s]: %s", stage, exc)


# ── routes ─────────────────────────────────────────────────────────────────────

@app.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok", "version": app.version}


@app.get("/pipeline/links", summary="iNFINITEAi2025 quad-pipeline links")
async def pipeline_links() -> dict:
    """Return direct links to each stage of the iNFINITEAi2025 quad pipeline on HuggingFace."""
    return {
        "pipeline": "iNFINITEAi2025",
        "account": "NaTo1000",
        "hub_url": "https://huggingface.co/NaTo1000/iNFINITEAi2025",
        "stages": HF_QUAD_ENDPOINTS,
    }


@app.post("/github", summary="GitHub webhook receiver")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str = Header(default=""),
) -> dict:
    """Receive a GitHub webhook event, validate the signature, and dispatch tasks."""
    payload_bytes = await request.body()
    _verify_signature(payload_bytes, x_hub_signature_256)

    data: dict = await request.json()
    dispatched: list[str] = []

    if x_github_event == "push":
        ref = data.get("ref", "")
        if ref == "refs/heads/dev":
            repack_pack.delay(pack_name=None)
            reindex.delay()
            dispatched = ["repack_pack", "reindex"]
            await _notify_hf_pipeline("repack",  {"ref": ref, "event": "push"})
            await _notify_hf_pipeline("reindex", {"ref": ref, "event": "push"})

    elif x_github_event == "pull_request":
        action = data.get("action", "")
        if action in ("opened", "synchronize"):
            check_pack.delay(pack_name=None)
            dispatched = ["check_pack"]
            await _notify_hf_pipeline("check", {"action": action, "event": "pull_request"})

    elif x_github_event == "release":
        action = data.get("action", "")
        if action == "published":
            repack_pack.delay(pack_name=None)
            generate_previews.delay(pack_name=None)
            reindex.delay()
            dispatched = ["repack_pack", "generate_previews", "reindex"]
            await _notify_hf_pipeline("repack",   {"action": action, "event": "release"})
            await _notify_hf_pipeline("previews", {"action": action, "event": "release"})
            await _notify_hf_pipeline("reindex",  {"action": action, "event": "release"})

    return {"dispatched": dispatched}


@app.post("/trigger/repack", summary="Manually trigger a repack")
async def trigger_repack(pack_name: str | None = None) -> dict:
    """Manually trigger a repack and notify the HuggingFace repack stage."""
    task = repack_pack.delay(pack_name=pack_name)
    await _notify_hf_pipeline("repack", {"pack_name": pack_name, "trigger": "manual"})
    return {"task_id": task.id, "pack_name": pack_name}


@app.post("/trigger/check", summary="Manually trigger a format check")
async def trigger_check(pack_name: str | None = None) -> dict:
    """Manually trigger a format check and notify the HuggingFace check stage."""
    task = check_pack.delay(pack_name=pack_name)
    await _notify_hf_pipeline("check", {"pack_name": pack_name, "trigger": "manual"})
    return {"task_id": task.id, "pack_name": pack_name}


@app.post("/trigger/previews", summary="Manually trigger preview generation")
async def trigger_previews(pack_name: str | None = None) -> dict:
    """Manually trigger preview generation and notify the HuggingFace previews stage."""
    task = generate_previews.delay(pack_name=pack_name)
    await _notify_hf_pipeline("previews", {"pack_name": pack_name, "trigger": "manual"})
    return {"task_id": task.id, "pack_name": pack_name}


@app.post("/trigger/reindex", summary="Manually trigger reindex")
async def trigger_reindex() -> dict:
    """Manually trigger reindex and notify the HuggingFace reindex stage."""
    task = reindex.delay()
    await _notify_hf_pipeline("reindex", {"trigger": "manual"})
    return {"task_id": task.id}
