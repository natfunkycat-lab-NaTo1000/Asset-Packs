#!/usr/bin/env python3
"""
ConductorX — Main Entrypoint (Component 1)

Runs the multi-agent conductor crew. The Conductor agent receives a task
description, then delegates to specialist agents (Packer, Checker,
Preview Generator, Indexer) in the correct order.

Usage:
  python conductor/main.py "repack the pokemon pack and reindex"
  python conductor/main.py "check all packs"
  python conductor/main.py "full release pipeline for starwars"
"""
import os
import sys

from crewai import Crew, Task

from conductor.agents.agents import (
    make_checker_agent,
    make_conductor_agent,
    make_indexer_agent,
    make_packer_agent,
    make_previews_agent,
)

# Optional: configure an LLM. Defaults to GPT-4o via OPENAI_API_KEY.
# You can swap in any CrewAI-compatible LLM.
LLM = None  # e.g. ChatOpenAI(model="gpt-4o") or Ollama(model="llama3")


def build_crew() -> Crew:
    conductor = make_conductor_agent(LLM)
    packer = make_packer_agent(LLM)
    checker = make_checker_agent(LLM)
    previewer = make_previews_agent(LLM)
    indexer = make_indexer_agent(LLM)

    orchestration_task = Task(
        description=(
            "You are the Conductor. Analyse the following user request and execute "
            "the appropriate asset pack operations in the correct order.\n\n"
            "Request: {user_request}\n\n"
            "Available operations:\n"
            "- check: verify pack format\n"
            "- repack: rebuild .zip and .tar.gz archives\n"
            "- previews: generate GIF previews from MP4s\n"
            "- reindex: trigger the Momentum website reindex\n\n"
            "Delegate subtasks to the specialist agents. Always check before packing, "
            "and always reindex after packing."
        ),
        expected_output=(
            "A summary of all operations performed, with output from each specialist agent."
        ),
        agent=conductor,
    )

    return Crew(
        agents=[conductor, packer, checker, previewer, indexer],
        tasks=[orchestration_task],
        verbose=True,
    )


def main() -> None:
    user_request = " ".join(sys.argv[1:]) if sys.argv[1:] else "check all packs"
    print(f"ConductorX starting — request: {user_request!r}")
    crew = build_crew()
    result = crew.kickoff(inputs={"user_request": user_request})
    print("\n=== ConductorX Result ===")
    print(result)


if __name__ == "__main__":
    main()
