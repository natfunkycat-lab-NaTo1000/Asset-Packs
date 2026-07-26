#!/usr/bin/env python3
"""
ConductorX — Agent Definitions (Component 1)

Specialized CrewAI agents for asset pack operations.
Each agent has a role, goal, backstory and a bound toolset.
"""
from crewai import Agent

from conductor.tools.pack_tools import CheckPackTool, GeneratePreviewsTool, RepackPackTool
from conductor.tools.system_tools import ReindexTool, WebhookTriggerTool


def make_packer_agent(llm=None) -> Agent:
    return Agent(
        role="Asset Pack Packer",
        goal=(
            "Repack Flipper Zero asset packs into their final .zip and .tar.gz "
            "distribution formats using the project tooling."
        ),
        backstory=(
            "You are a precise packaging engineer. You take raw asset sources and "
            "produce deterministic, compressed archives ready for distribution."
        ),
        tools=[RepackPackTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def make_checker_agent(llm=None) -> Agent:
    return Agent(
        role="Asset Pack Checker",
        goal=(
            "Verify that asset pack directories conform to the expected format: "
            "correct structure, valid meta.json, presence of previews and downloads."
        ),
        backstory=(
            "You are a meticulous QA engineer who ensures every pack meets the "
            "Momentum Firmware asset pack specification before it ships."
        ),
        tools=[CheckPackTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def make_previews_agent(llm=None) -> Agent:
    return Agent(
        role="Preview Generator",
        goal="Generate GIF preview images from MP4 recordings of asset packs.",
        backstory=(
            "You are a media processing specialist. You convert screen recordings "
            "into preview GIFs that users see on the Momentum website."
        ),
        tools=[GeneratePreviewsTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def make_indexer_agent(llm=None) -> Agent:
    return Agent(
        role="Indexer",
        goal="Trigger the remote asset pack reindex so the Momentum website stays current.",
        backstory=(
            "You are responsible for keeping the public API in sync with the latest "
            "published asset packs by firing the indexer webhook."
        ),
        tools=[ReindexTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def make_conductor_agent(llm=None) -> Agent:
    return Agent(
        role="Conductor",
        goal=(
            "Orchestrate asset pack operations by routing incoming requests to the "
            "correct specialist agents: Packer, Checker, Preview Generator, or Indexer."
        ),
        backstory=(
            "You are the ConductorX orchestration agent. You analyse incoming events "
            "and task descriptions, then delegate to the right specialist. You ensure "
            "tasks run in the correct order: check → repack → previews → reindex."
        ),
        tools=[WebhookTriggerTool()],
        llm=llm,
        verbose=True,
        allow_delegation=True,
    )
