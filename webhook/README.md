# ConductorX — Webhook Server (Component 4) v2

FastAPI server that receives GitHub webhook events, dispatches Celery tasks to
the worker mesh, and forwards notifications to the
[iNFINITEAi2025 quad pipeline](https://huggingface.co/NaTo1000/iNFINITEAi2025)
on HuggingFace.

Manual `/trigger/*` endpoints are protected by a JWT issued by the payment
server — see [`payment/`](../payment/README.md).

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GITHUB_WEBHOOK_SECRET` | ✅ prod | GitHub webhook HMAC-SHA256 secret |
| `CELERY_BROKER_URL` | ✅ | Redis broker URL (default: `redis://localhost:6379/0`) |
| `CELERY_RESULT_BACKEND` | | Redis result backend (default: same as broker) |
| `HF_API_TOKEN` | | HuggingFace API token (`hf_...`) for quad-pipeline notifications |
| `HF_PIPELINE_URL` | | Override quad-pipeline base URL (default: `https://huggingface.co/NaTo1000/iNFINITEAi2025`) |
| `JWT_SECRET` | ✅ prod | Shared secret for validating payment-issued JWTs on `/trigger/*` |

## Running Locally

```bash
cd webhook
pip install -r requirements.txt
uvicorn webhook.main:app --reload
```

## Running with Docker

```bash
docker build -f webhook/Dockerfile -t conductor-webhook .
docker run -p 8000:8000 \
  -e GITHUB_WEBHOOK_SECRET=your_secret \
  -e CELERY_BROKER_URL=redis://your-mesh-node:6379/0 \
  -e HF_API_TOKEN=hf_... \
  -e JWT_SECRET=your_jwt_secret \
  conductor-webhook
```

## GitHub Webhook Setup

1. Go to your repo → **Settings → Webhooks → Add webhook**
2. **Payload URL**: `https://<your-domain>/github`
3. **Content type**: `application/json`
4. **Secret**: value of `GITHUB_WEBHOOK_SECRET`
5. **Events**: ✅ Push · ✅ Pull requests · ✅ Releases

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Health check |
| GET | `/pipeline/links` | — | iNFINITEAi2025 quad-pipeline links |
| POST | `/github` | HMAC sig | GitHub webhook receiver |
| POST | `/trigger/repack?pack_name=foo` | JWT | Manually trigger repack |
| POST | `/trigger/check?pack_name=foo` | JWT | Manually trigger check |
| POST | `/trigger/previews?pack_name=foo` | JWT | Manually trigger previews |
| POST | `/trigger/reindex` | JWT | Manually trigger reindex |

### Using the JWT

After purchasing access via the payment server, include your token:

```bash
curl -X POST https://<your-domain>/trigger/repack \
  -H "Authorization: ******"
```
