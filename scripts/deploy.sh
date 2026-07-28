#!/usr/bin/env bash
# ConductorX — First-time deployment script
#
# Usage:
#   cp .env.example .env && nano .env   # fill in all secrets
#   bash scripts/deploy.sh
#
# What it does:
#   1. Validates .env — exits if required variables are missing
#   2. Joins the Tailscale mesh
#   3. Pulls latest images from GHCR
#   4. Starts the full stack with docker compose
#   5. Waits for all services to pass health checks
#   6. Prints the service URLs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.prod.yml"
ENV_FILE="${REPO_ROOT}/.env"

# ── colour helpers ─────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[deploy]${NC} $*"; }
warning() { echo -e "${YELLOW}[deploy]${NC} $*"; }
error()   { echo -e "${RED}[deploy]${NC} $*" >&2; }

# ── 1. validate .env ───────────────────────────────────────────────────────────
info "Checking .env..."
if [[ ! -f "${ENV_FILE}" ]]; then
  error ".env not found. Copy .env.example and fill it in:"
  error "  cp .env.example .env && nano .env"
  exit 1
fi

set -a; source "${ENV_FILE}"; set +a

REQUIRED_VARS=(
  GITHUB_WEBHOOK_SECRET
  JWT_SECRET
  TAILSCALE_AUTH_KEY
  PAYPAL_CLIENT_ID
  PAYPAL_CLIENT_SECRET
  PAYPAL_MODE
  DOMAIN
)

MISSING=()
for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    MISSING+=("$var")
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  error "The following required variables are not set in .env:"
  for v in "${MISSING[@]}"; do
    error "  • $v"
  done
  exit 1
fi
info "All required variables are set."

# ── 2. join Tailscale mesh ─────────────────────────────────────────────────────
info "Joining Tailscale mesh..."
bash "${REPO_ROOT}/mesh/setup.sh"

# ── 3. pull latest images ──────────────────────────────────────────────────────
info "Pulling latest images..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" pull --quiet

# ── 4. start the stack ────────────────────────────────────────────────────────
info "Starting full stack..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --remove-orphans

# ── 5. wait for health checks ─────────────────────────────────────────────────
info "Waiting for services to become healthy (up to 90s)..."
bash "${SCRIPT_DIR}/healthcheck.sh"

# ── 6. print URLs ─────────────────────────────────────────────────────────────
info "Deployment complete!"
echo ""
echo "  🌐  Payment wall:  https://${DOMAIN}/"
echo "  🔗  Webhook:       https://${DOMAIN}/github"
echo "  🔗  Pipeline links: https://${DOMAIN}/pipeline/links"
echo "  📊  Flower UI:     http://$(tailscale ip -4 2>/dev/null || echo 'localhost'):5555"
echo ""
echo "Next steps:"
echo "  1. Register the GitHub webhook: https://${DOMAIN}/github"
echo "     (Settings → Webhooks → Add webhook, secret = GITHUB_WEBHOOK_SECRET)"
echo "  2. Set PAYPAL_MODE=live in .env when ready for production payments."
