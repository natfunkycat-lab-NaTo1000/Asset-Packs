# ConductorX — Payment Server

FastAPI app that presents a **PayPal payment wall** and issues signed JWTs
after successful payment.  JWTs are validated by the webhook server on all
manual `/trigger/*` endpoints.

## Architecture

```
User → GET  /                   → pricing page
User → POST /order/create       → gets PayPal approval URL
User → PayPal approval page     → pays
PayPal → GET /order/capture     → payment captured → JWT issued
User → POST /trigger/repack (webhook server, Authorization: ******
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `PAYPAL_CLIENT_ID` | ✅ | From [developer.paypal.com](https://developer.paypal.com) → My Apps |
| `PAYPAL_CLIENT_SECRET` | ✅ | Same app |
| `PAYPAL_MODE` | ✅ | `sandbox` (testing) or `live` (production) |
| `PAYPAL_WEBHOOK_ID` | | PayPal webhook ID for event verification |
| `JWT_SECRET` | ✅ | Shared with webhook server — `openssl rand -hex 32` |
| `JWT_ACCESS_DAYS` | | Days the issued token is valid (default: `365`) |
| `PRICE_USD` | | One-time purchase price (default: `9.99`) |
| `SUBSCRIPTION_PLAN_ID` | | PayPal billing plan ID for recurring access |
| `DOMAIN` | ✅ prod | Public domain used to build callback URLs (e.g. `yourdomain.com`) |

## Running Locally

```bash
cd payment
pip install -r requirements.txt
PAYPAL_MODE=sandbox PAYPAL_CLIENT_ID=... PAYPAL_CLIENT_SECRET=... \
  JWT_SECRET=$(openssl rand -hex 32) \
  uvicorn payment.main:app --reload --port 8001
```

## Running with Docker

```bash
docker build -f payment/Dockerfile -t conductor-payment .
docker run -p 8001:8001 \
  -e PAYPAL_CLIENT_ID=... \
  -e PAYPAL_CLIENT_SECRET=... \
  -e PAYPAL_MODE=sandbox \
  -e JWT_SECRET=your_jwt_secret \
  -e PRICE_USD=9.99 \
  -e DOMAIN=yourdomain.com \
  conductor-payment
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/` | Pricing information |
| POST | `/order/create` | Create a PayPal Order |
| GET | `/order/capture?token=` | PayPal redirect — capture payment, issue JWT |
| GET | `/order/cancel` | User cancelled checkout |
| POST | `/subscription/create` | Create a PayPal Subscription |
| GET | `/subscription/activate?subscription_id=` | PayPal redirect — verify subscription, issue JWT |
| GET | `/subscription/cancel` | User cancelled subscription |

## PayPal Setup (first time)

### One-time purchase
1. Log in to [developer.paypal.com](https://developer.paypal.com)
2. Go to **My Apps & Credentials → Create App**
3. Copy `Client ID` and `Secret` into your `.env`
4. Set `PAYPAL_MODE=sandbox` for testing, `live` for production

### Recurring subscription
1. In the PayPal Developer Dashboard go to **Billing Plans → Create plan**
2. Set billing cycle (e.g. monthly $4.99)
3. Copy the plan ID → set `SUBSCRIPTION_PLAN_ID` in `.env`
