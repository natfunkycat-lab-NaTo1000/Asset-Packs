# ConductorX — Gateway (TLS Reverse Proxy)

Two options for TLS termination and reverse proxying. Choose one:

| | nginx | Caddy |
|---|---|---|
| TLS management | Manual (certbot) | Automatic (Let's Encrypt) |
| Config file | `nginx.conf` | `Caddyfile` |
| Complexity | Higher | Lower |

## Option A — Caddy (recommended, auto-TLS)

```bash
# Install Caddy
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install caddy

# Copy config and reload
cp gateway/Caddyfile /etc/caddy/Caddyfile
systemctl reload caddy
```

Or use the Docker approach in `docker-compose.prod.yml` (the `caddy` service).

## Option B — nginx (manual cert via certbot)

```bash
apt install -y nginx certbot python3-certbot-nginx
cp gateway/nginx.conf /etc/nginx/sites-available/conductorx
ln -s /etc/nginx/sites-available/conductorx /etc/nginx/sites-enabled/
certbot --nginx -d yourdomain.com
nginx -t && systemctl reload nginx
```

## Routing Table

| Path prefix | Upstream |
|---|---|
| `/github`, `/health`, `/pipeline/links`, `/trigger/*` | `webhook:8000` |
| `/`, `/order/*`, `/subscription/*` | `payment:8001` |
