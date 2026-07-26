#!/usr/bin/env python3
"""
ConductorX — System Tools

CrewAI tools for system-level operations: triggering the indexer
and invoking webhook endpoints on other mesh nodes.
"""
import os
import urllib.request

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ReindexTool(BaseTool):
    name: str = "reindex"
    description: str = "Trigger the Momentum Firmware asset pack reindex via the indexer API."

    def _run(self) -> str:
        indexer_url = os.environ.get("INDEXER_URL", "")
        indexer_token = os.environ.get("INDEXER_TOKEN", "")
        if not indexer_url:
            return "Skipped: INDEXER_URL is not configured."
        req = urllib.request.Request(
            f"{indexer_url}/asset-packs/reindex",
            headers={"Token": indexer_token},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
        return f"Reindex triggered. Response: {body}"


class WebhookTriggerInput(BaseModel):
    endpoint: str = Field(
        description="Webhook path to call, e.g. '/trigger/repack' or '/trigger/check'."
    )
    pack_name: str | None = Field(default=None, description="Optional pack name query param.")


class WebhookTriggerTool(BaseTool):
    name: str = "webhook_trigger"
    description: str = (
        "Trigger a ConductorX webhook endpoint on the local or remote webhook server. "
        "Use this to enqueue tasks (repack, check, previews, reindex) via the HTTP API."
    )
    args_schema: type[BaseModel] = WebhookTriggerInput

    def _run(self, endpoint: str, pack_name: str | None = None) -> str:
        base_url = os.environ.get("CONDUCTOR_WEBHOOK_URL", "http://localhost:8000")
        url = f"{base_url}{endpoint}"
        if pack_name:
            url += f"?pack_name={pack_name}"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
        return f"Triggered {endpoint}. Response: {body}"
