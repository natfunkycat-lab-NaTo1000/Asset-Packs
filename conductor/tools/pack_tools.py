#!/usr/bin/env python3
"""
ConductorX — Pack Operation Tools

CrewAI tools that wrap the existing .utils Python scripts.
These tools are given to specialist agents so they can invoke
pack operations as structured tool calls.
"""
import subprocess
import sys
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


REPO_ROOT = Path(__file__).parent.parent.parent


class PackNameInput(BaseModel):
    pack_name: str | None = Field(
        default=None,
        description="Name of a single asset pack directory to process, or null for all packs.",
    )


def _run_util(script: str, pack_name: str | None) -> str:
    cmd = [sys.executable, f".utils/{script}"]
    if pack_name:
        cmd.append(pack_name)
    result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(f"{script} failed:\n{output}")
    return output


class RepackPackTool(BaseTool):
    name: str = "repack_pack"
    description: str = (
        "Repack one or all asset packs into .zip and .tar.gz archives. "
        "Pass a pack_name to repack a single pack, or leave blank for all."
    )
    args_schema: type[BaseModel] = PackNameInput

    def _run(self, pack_name: str | None = None) -> str:
        return _run_util("repack.py", pack_name)


class CheckPackTool(BaseTool):
    name: str = "check_pack"
    description: str = (
        "Check the format of one or all asset packs. "
        "Returns a summary of any format violations found."
    )
    args_schema: type[BaseModel] = PackNameInput

    def _run(self, pack_name: str | None = None) -> str:
        return _run_util("check.py", pack_name)


class GeneratePreviewsTool(BaseTool):
    name: str = "generate_previews"
    description: str = (
        "Generate GIF preview images from MP4 recordings for one or all packs."
    )
    args_schema: type[BaseModel] = PackNameInput

    def _run(self, pack_name: str | None = None) -> str:
        return _run_util("previews.py", pack_name)
