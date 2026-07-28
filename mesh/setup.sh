#!/usr/bin/env bash
# ConductorX Mesh Setup — joins this device to the Tailscale mesh network.
# Run once on every device: VPS, home server, laptop, etc.
#
# Usage:
#   export TAILSCALE_AUTH_KEY=tskey-auth-xxxxx
#   bash mesh/setup.sh
#
# On mobile/tablet: install the Tailscale app and log in with the same account.

set -euo pipefail

HOSTNAME="${CONDUCTOR_HOSTNAME:-$(hostname)}"

if [[ -z "${TAILSCALE_AUTH_KEY:-}" ]]; then
  echo "ERROR: TAILSCALE_AUTH_KEY environment variable must be set." >&2
  echo "Get one from https://login.tailscale.com/admin/settings/keys" >&2
  exit 1
fi

# Install Tailscale if not already present
if ! command -v tailscale &>/dev/null; then
  echo "Installing Tailscale..."
  curl -fsSL https://tailscale.com/install.sh | sh
else
  echo "Tailscale already installed: $(tailscale version)"
fi

# Join the mesh
echo "Joining Tailscale mesh as '${HOSTNAME}'..."
tailscale up \
  --authkey="${TAILSCALE_AUTH_KEY}" \
  --hostname="${HOSTNAME}" \
  --accept-routes

echo "Done. This device is now part of the ConductorX mesh."
echo "Tailscale IP: $(tailscale ip -4 2>/dev/null || echo 'pending')"
