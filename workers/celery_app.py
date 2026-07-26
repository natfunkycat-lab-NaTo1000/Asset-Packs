#!/usr/bin/env python3
"""
ConductorX Workers (Component 2)
Celery app with task definitions for all asset pack operations.
Each task runs the existing make/python tooling inside the repo.
"""
import os
import subprocess
import sys
from pathlib import Path

from celery import Celery

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", BROKER_URL)
REPO_ROOT = Path(os.environ.get("REPO_ROOT", Path(__file__).parent.parent))

app = Celery("conductor", broker=BROKER_URL, backend=RESULT_BACKEND)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)


def _run(cmd: list[str]) -> str:
    """Run a command in the repo root and return combined stdout+stderr."""
    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise RuntimeError(f"Command {cmd} failed:\n{output}")
    return output


@app.task(bind=True, name="conductor.repack_pack", max_retries=2)
def repack_pack(self, pack_name: str | None = None) -> dict:
    """Repack one or all asset packs."""
    cmd = [sys.executable, ".utils/repack.py"]
    if pack_name:
        cmd.append(pack_name)
    output = _run(cmd)
    return {"pack_name": pack_name, "output": output}


@app.task(bind=True, name="conductor.check_pack", max_retries=2)
def check_pack(self, pack_name: str | None = None) -> dict:
    """Check the format of one or all asset packs."""
    cmd = [sys.executable, ".utils/check.py"]
    if pack_name:
        cmd.append(pack_name)
    output = _run(cmd)
    return {"pack_name": pack_name, "output": output}


@app.task(bind=True, name="conductor.generate_previews", max_retries=2)
def generate_previews(self, pack_name: str | None = None) -> dict:
    """Generate previews for one or all asset packs."""
    cmd = [sys.executable, ".utils/previews.py"]
    if pack_name:
        cmd.append(pack_name)
    output = _run(cmd)
    return {"pack_name": pack_name, "output": output}


@app.task(bind=True, name="conductor.reindex", max_retries=3)
def reindex(self) -> dict:
    """Trigger the asset pack reindex via the indexer API."""
    import urllib.request

    indexer_url = os.environ.get("INDEXER_URL", "")
    indexer_token = os.environ.get("INDEXER_TOKEN", "")
    if not indexer_url:
        return {"status": "skipped", "reason": "INDEXER_URL not set"}
    req = urllib.request.Request(
        f"{indexer_url}/asset-packs/reindex",
        headers={"Token": indexer_token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
    except OSError as exc:
        raise RuntimeError(f"Failed to reach indexer: {exc}") from exc
    return {"status": "ok", "response": body}
