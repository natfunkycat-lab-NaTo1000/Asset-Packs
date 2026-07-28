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
| Webhook Server | [`webhook/`](webhook/README.md) | FastAPI GitHub webhook receiver + HuggingFace pipeline links |
| Payment Server | [`payment/`](payment/README.md) | PayPal payment wall — issues JWTs for API access |
| Gateway | [`gateway/`](gateway/README.md) | nginx / Caddy TLS reverse proxy |
| Quantum Sampler | [`quantum/`](quantum/README.md) | IBM Quantum / Qiskit hybrid |
| Device Mesh | [`mesh/`](mesh/README.md) | Tailscale private mesh network |

### HuggingFace Quad Pipeline

The webhook server connects directly to the
[iNFINITEAi2025 quad pipeline](https://huggingface.co/NaTo1000/iNFINITEAi2025)
on HuggingFace account **NaTo1000**.  Every GitHub event (push/PR/release)
notifies the matching pipeline stage (check → repack → previews → reindex).

View live pipeline links at runtime:
```
GET https://<your-domain>/pipeline/links
```

---

### Hardware Minimums

#### Control-Plane VPS (Redis · webhook · Caddy · Tailscale relay)

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Disk | 20 GB SSD | 40 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Uplink | 100 Mbps | 1 Gbps |
| Kernel | 5.15+ (TUN/TAP required for Tailscale) | 6.x |

#### Worker Nodes (Celery — laptop / home server / cloud VM)

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 2 cores | 4 cores |
| RAM | 2 GB | 4 GB |
| Disk free | 10 GB | 20 GB |
| Python | 3.11 | 3.11 |
| Docker | 24+ | 25+ |
| ffmpeg | 6.x | 6.x |

#### Payment Gateway Server

| Resource | Minimum |
|---|---|
| CPU | 1 vCPU |
| RAM | 512 MB |
| TLS certificate | Required (Caddy auto-provisions via Let's Encrypt) |
| Public IP | Required (no NAT) |
| Port 443 inbound | Open |

---

### Full-Stack Production Quick Start

**Prerequisites on your VPS:**
```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin

# Clone repo
git clone https://github.com/natfunkycat-lab-NaTo1000/Asset-Packs.git
cd Asset-Packs

# Fill in all secrets
cp .env.example .env
nano .env
```

**First-time deploy (single command):**
```bash
bash scripts/deploy.sh
```

This will:
1. Validate all required env vars in `.env`
2. Join the Tailscale mesh
3. Pull latest images from GHCR
4. Start the full stack (`docker-compose.prod.yml`)
5. Wait for health checks on all services
6. Print your service URLs

**Register the GitHub Webhook:**
1. Go to repo → **Settings → Webhooks → Add webhook**
2. **Payload URL**: `https://<your-domain>/github`
3. **Content type**: `application/json`
4. **Secret**: value of `GITHUB_WEBHOOK_SECRET` in `.env`
5. **Events**: ✅ Push · ✅ Pull requests · ✅ Releases

**Access the payment wall:**
- Visit `https://<your-domain>/` to see pricing
- After purchase, use the issued JWT on trigger endpoints:
  ```bash
  curl -X POST https://<your-domain>/trigger/repack \
    -H "Authorization: ******"
  ```

**Rolling updates (zero downtime):**
```bash
bash scripts/update.sh v1.2.0    # specific tag
bash scripts/update.sh latest    # latest
```

**Rollback:**
```bash
bash scripts/rollback.sh v1.1.0
```

**Individual component quick start (dev mode):**

```bash
# 1. Mesh + Redis
export TAILSCALE_AUTH_KEY=tskey-auth-xxxxx
docker compose -f mesh/docker-compose.tailscale.yml up -d

# 2. Worker
export CELERY_BROKER_URL=redis://<mesh-redis-ip>:6379/0
docker compose -f workers/docker-compose.yml up -d

# 3. Webhook server (dev — no JWT required)
docker build -f webhook/Dockerfile -t conductor-webhook .
docker run -p 8000:8000 -e CELERY_BROKER_URL -e GITHUB_WEBHOOK_SECRET=secret \
  -e HF_API_TOKEN=hf_... conductor-webhook

# 4. Payment server (sandbox mode)
docker build -f payment/Dockerfile -t conductor-payment .
docker run -p 8001:8001 \
  -e PAYPAL_MODE=sandbox -e PAYPAL_CLIENT_ID=... -e PAYPAL_CLIENT_SECRET=... \
  -e JWT_SECRET=$(openssl rand -hex 32) -e DOMAIN=localhost:8001 \
  conductor-payment

# 5. Conductor agent
pip install -r conductor/requirements.txt
export OPENAI_API_KEY=your_key
python conductor/main.py "check all packs and reindex"
```

**Trigger via GitHub Actions:**
Go to Actions → Conductor → Run workflow, enter a natural language request.