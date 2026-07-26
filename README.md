# Asset-Packs
Bundle of [asset packs](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/documentation/file_formats/AssetPacks.md) for [Momentum Firmware](https://github.com/Next-Flip/Momentum-Firmware).

> [!IMPORTANT]
> These asset packs are all available on the [Momentum Firmware website](https://momentum-fw.dev/asset-packs).
> This repository serves only as a way to keep them updated and maintained easier.

### How?
The [flipper-update-indexer](https://github.com/Next-Flip/flipper-update-indexer) includes this repository as a submodule. It will parse the asset packs contents and serve the appropriate files on the API ([`https://up.momentum-fw.dev/asset-packs`](https://up.momentum-fw.dev/asset-packs)). Then the [Momentum-Website](https://github.com/Next-Flip/Momentum-Website) will query the API and allow users to download and install the asset packs.

The scope of this repo is keeping the asset packs themselves updated and recompile them as needed.

You can do this by:
```bash
    make repack [pack-name]
    # OR
    python .utils/repack.py [pack-name]
```

Currently we don't have a convenient way of generating previews. For now what we do is:
- For Icons: use [qFlipper](https://flipperzero.one/update), click 'Save Screenshot'
- For Anims: use [qFlipper](https://flipperzero.one/update), record it, put `.mp4` in `pack-name/preview` folder, run `make previews [pack-name]` (or `python .utils/previews.py [pack-name]`) to convert to `.gif`
  - To make cropping easier, you can use [Blue Recorder](https://flathub.org/apps/sa.sy.bluerecorder)'s Window capture: the above script will notice the right pixel sizes (862x532) and crop to fit qFlipper's preview

### Docker

A Docker image with the tooling pre-installed is published to [GitHub Container Registry](https://ghcr.io/natfunkycat-lab-nato1000/asset-packs) on every push to `dev` and on version tags.

You can use it to run pack operations without installing Python or ffmpeg locally:
```bash
docker pull ghcr.io/natfunkycat-lab-nato1000/asset-packs:latest
docker run --rm -v $(pwd):/workspace ghcr.io/natfunkycat-lab-nato1000/asset-packs:latest python3 .utils/repack.py [pack-name]
```

Or build the image locally:
```bash
make docker-build
```

---

## ConductorX — Multi-Agent Orchestration

ConductorX is a multi-component orchestration system layered on top of the CI/CD
infrastructure. Each component is independently deployable.

| Component | Directory | Description |
|---|---|---|
| Agent Orchestration | [`conductor/`](conductor/README.md) | CrewAI multi-agent system |
| Distributed Workers | [`workers/`](workers/) | Celery task queue across devices |
| Webhook Server | [`webhook/`](webhook/README.md) | FastAPI GitHub webhook receiver |
| Quantum Sampler | [`quantum/`](quantum/README.md) | IBM Quantum / Qiskit hybrid |
| Device Mesh | [`mesh/`](mesh/README.md) | Tailscale private mesh network |

### Quick Start

**1. Connect devices to the mesh:**
```bash
export TAILSCALE_AUTH_KEY=tskey-auth-xxxxx
bash mesh/setup.sh
```

**2. Start Redis + Tailscale (on your home server / VPS):**
```bash
export TAILSCALE_AUTH_KEY=tskey-auth-xxxxx
docker compose -f mesh/docker-compose.tailscale.yml up -d
```

**3. Start a worker (on any mesh device):**
```bash
export CELERY_BROKER_URL=redis://<mesh-redis-ip>:6379/0
docker compose -f workers/docker-compose.yml up -d
```

**4. Start the webhook server (on your VPS):**
```bash
export CELERY_BROKER_URL=redis://<mesh-redis-ip>:6379/0
export GITHUB_WEBHOOK_SECRET=your_secret
docker build -f webhook/Dockerfile -t conductor-webhook .
docker run -p 8000:8000 -e CELERY_BROKER_URL -e GITHUB_WEBHOOK_SECRET conductor-webhook
```

**5. Run the conductor agent:**
```bash
pip install -r conductor/requirements.txt
export OPENAI_API_KEY=your_key
python conductor/main.py "check all packs and reindex"
```

**6. Trigger via GitHub Actions:**
Go to Actions → Conductor → Run workflow, enter a natural language request.