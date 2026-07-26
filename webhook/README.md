# ConductorX — Webhook Server (Component 4)

Lightweight FastAPI server that receives GitHub webhook events and dispatches
Celery tasks to the worker mesh.

## Environment Variables

| Variable | Description |
|---|---|
| `GITHUB_WEBHOOK_SECRET` | GitHub webhook secret for HMAC validation |
| `CELERY_BROKER_URL` | Redis broker URL (default: `redis://localhost:6379/0`) |
| `CELERY_RESULT_BACKEND` | Redis result backend (default: same as broker) |

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
  conductor-webhook
```

## GitHub Webhook Setup

1. Go to your repo → Settings → Webhooks → Add webhook
2. **Payload URL**: `https://your-vps.tail12345.ts.net:8000/github`
3. **Content type**: `application/json`
4. **Secret**: set `GITHUB_WEBHOOK_SECRET` to the same value
5. **Events**: Push, Pull requests, Releases

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/github` | GitHub webhook receiver |
| POST | `/trigger/repack?pack_name=foo` | Manually trigger repack |
| POST | `/trigger/check?pack_name=foo` | Manually trigger check |
| POST | `/trigger/previews?pack_name=foo` | Manually trigger previews |
| POST | `/trigger/reindex` | Manually trigger reindex |
