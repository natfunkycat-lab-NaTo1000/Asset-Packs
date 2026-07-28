# ConductorX — Mesh Network (Component 5)

Connects all devices (VPS, home server, laptop, mobile, tablet) into a private
mesh network using [Tailscale](https://tailscale.com/). No port forwarding needed.

## Setup

### Bare-metal / VM / Laptop
```bash
export TAILSCALE_AUTH_KEY=tskey-auth-xxxxx   # from https://login.tailscale.com/admin/settings/keys
export CONDUCTOR_HOSTNAME=my-homelab         # any friendly name
bash mesh/setup.sh
```

### Docker (run alongside other services)
```bash
export TAILSCALE_AUTH_KEY=tskey-auth-xxxxx
export CONDUCTOR_HOSTNAME=my-vps
docker compose -f mesh/docker-compose.tailscale.yml up -d
```

This also starts a Redis instance on the mesh, which workers and the webhook
server use as the Celery broker.

### Mobile / Tablet
Install the [Tailscale app](https://tailscale.com/download) and log in with the
same Tailscale account. The device joins automatically.

## After Setup

All mesh nodes can reach each other by hostname:
```
conductor-redis.tail12345.ts.net:6379   # Redis broker
conductor-webhook.tail12345.ts.net:8000 # Webhook server
```

Use `tailscale status` to see all connected devices.
