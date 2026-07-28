#!/usr/bin/env bash
# ConductorX — Health check script
#
# Usage:
#   bash scripts/healthcheck.sh
#
# Checks /health on the webhook and payment servers.
# Retries for up to 90 seconds before declaring failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[health]${NC} $*"; }
error() { echo -e "${RED}[health]${NC} $*" >&2; }

if [[ -f "${ENV_FILE}" ]]; then
  set -a; source "${ENV_FILE}"; set +a
fi

WEBHOOK_URL="${WEBHOOK_HEALTH_URL:-http://localhost:8000/health}"
PAYMENT_URL="${PAYMENT_HEALTH_URL:-http://localhost:8001/health}"
MAX_WAIT=90
INTERVAL=5

check_url() {
  local name="$1"
  local url="$2"
  local elapsed=0

  while [[ $elapsed -lt $MAX_WAIT ]]; do
    if curl --silent --fail --max-time 5 "${url}" > /dev/null 2>&1; then
      info "${name} is healthy (${url})"
      return 0
    fi
    sleep "${INTERVAL}"
    elapsed=$(( elapsed + INTERVAL ))
    info "Waiting for ${name}... (${elapsed}s / ${MAX_WAIT}s)"
  done

  error "${name} did not become healthy within ${MAX_WAIT}s (${url})"
  return 1
}

FAILED=0
check_url "webhook"  "${WEBHOOK_URL}"  || FAILED=$(( FAILED + 1 ))
check_url "payment"  "${PAYMENT_URL}"  || FAILED=$(( FAILED + 1 ))

if [[ $FAILED -gt 0 ]]; then
  error "${FAILED} service(s) failed health checks."
  exit 1
fi

info "All services are healthy."
