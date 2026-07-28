#!/usr/bin/env bash
# ConductorX — Rollback script
#
# Usage:
#   bash scripts/rollback.sh <IMAGE_TAG>
#   bash scripts/rollback.sh v1.1.0
#
# Redeoys all services using the specified image tag.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.prod.yml"
ENV_FILE="${REPO_ROOT}/.env"
IMAGE_TAG="${1:-}"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[rollback]${NC} $*"; }
error() { echo -e "${RED}[rollback]${NC} $*" >&2; }

if [[ -z "${IMAGE_TAG}" ]]; then
  error "Usage: bash scripts/rollback.sh <IMAGE_TAG>"
  error "Example: bash scripts/rollback.sh v1.1.0"
  exit 1
fi

if [[ -f "${ENV_FILE}" ]]; then
  set -a; source "${ENV_FILE}"; set +a
fi

GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-natfunkycat-lab-nato1000/asset-packs}"
IMAGE="ghcr.io/$(echo "${GITHUB_REPOSITORY}" | tr '[:upper:]' '[:lower:]')"

info "Rolling back to ${IMAGE}:${IMAGE_TAG}..."
docker pull "${IMAGE}:${IMAGE_TAG}"

export IMAGE_TAG
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
  up -d --remove-orphans

info "Verifying health after rollback..."
bash "${SCRIPT_DIR}/healthcheck.sh"

info "Rollback to ${IMAGE_TAG} complete."
