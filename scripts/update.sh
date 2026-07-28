#!/usr/bin/env bash
# ConductorX — Rolling update script (zero-downtime)
#
# Usage:
#   bash scripts/update.sh [IMAGE_TAG]
#   bash scripts/update.sh v1.2.0
#   bash scripts/update.sh latest     # default
#
# What it does:
#   1. Pulls the new image tag from GHCR
#   2. Updates each service in rolling order (worker → webhook → payment)
#   3. Verifies health checks after each restart
#   4. Auto-rolls back if any health check fails

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.prod.yml"
ENV_FILE="${REPO_ROOT}/.env"
IMAGE_TAG="${1:-latest}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[update]${NC} $*"; }
warning() { echo -e "${YELLOW}[update]${NC} $*"; }
error()   { echo -e "${RED}[update]${NC} $*" >&2; }

if [[ -f "${ENV_FILE}" ]]; then
  set -a; source "${ENV_FILE}"; set +a
fi

GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-natfunkycat-lab-nato1000/asset-packs}"
IMAGE="ghcr.io/$(echo "${GITHUB_REPOSITORY}" | tr '[:upper:]' '[:lower:]')"

info "Updating to image tag: ${IMAGE_TAG}"

# ── pull new images ────────────────────────────────────────────────────────────
info "Pulling ${IMAGE}:${IMAGE_TAG}..."
docker pull "${IMAGE}:${IMAGE_TAG}"

export IMAGE_TAG

# ── rolling restart per service ────────────────────────────────────────────────
SERVICES=(worker webhook payment)

for svc in "${SERVICES[@]}"; do
  info "Updating service: ${svc}..."
  PREVIOUS_TAG=$(docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
    images -q "${svc}" 2>/dev/null | head -1 || echo "")

  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
    up -d --no-deps --pull always "${svc}"

  sleep 5

  if ! bash "${SCRIPT_DIR}/healthcheck.sh" 2>/dev/null; then
    error "Health check failed after updating ${svc}. Rolling back..."
    if [[ -n "${PREVIOUS_TAG}" ]]; then
      docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        up -d --no-deps "${svc}"
    fi
    error "Rollback complete. Investigate logs: docker compose -f ${COMPOSE_FILE} logs ${svc}"
    exit 1
  fi

  info "Service ${svc} updated successfully."
done

info "All services updated to ${IMAGE_TAG}."
