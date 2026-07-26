# ConductorX — Multi-Agent Orchestration (Component 1)

CrewAI-powered multi-agent system that orchestrates asset pack operations.
A **Conductor** agent receives natural language requests and delegates to
specialist agents: **Packer**, **Checker**, **Preview Generator**, and **Indexer**.

## Setup

```bash
pip install -r conductor/requirements.txt
```

The conductor uses an LLM to reason about which operations to run. Set one of:
- `OPENAI_API_KEY` — for OpenAI GPT-4o (default)
- Or configure a local model (Ollama, LM Studio) by editing `conductor/main.py`

## Usage

```bash
# Check all packs
python conductor/main.py "check all packs"

# Repack a single pack and reindex
python conductor/main.py "repack the pokemon pack and reindex"

# Full release pipeline
python conductor/main.py "full release pipeline for starwars"

# Custom request
python conductor/main.py "generate previews for the pikachu-enfadao pack"
```

## Agent Roster

| Agent | Role | Tools |
|---|---|---|
| Conductor | Routes tasks to specialists | `webhook_trigger` |
| Packer | Builds .zip / .tar.gz archives | `repack_pack` |
| Checker | Validates pack format | `check_pack` |
| Preview Generator | Converts MP4 → GIF | `generate_previews` |
| Indexer | Fires reindex webhook | `reindex` |

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | LLM API key |
| `INDEXER_URL` | Momentum indexer API base URL |
| `INDEXER_TOKEN` | Momentum indexer auth token |
| `CONDUCTOR_WEBHOOK_URL` | Webhook server base URL (default: `http://localhost:8000`) |
