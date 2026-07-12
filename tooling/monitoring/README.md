# Monitoring stack — GlitchTip + Uptime Kuma

Self-hosted monitoring for the Mascope fleet, meant to run on the internal
**backup box `192.168.1.88`**, LAN-only (`192.168.1.0/24`), plain HTTP:

- **GlitchTip** — error tracking. Mascope's backend forwards `WARNING`/`ERROR`
  log records (with tracebacks and request context) so you stop grepping log
  files. Sentry-API compatible; Mascope uses the stock `sentry-sdk`.
- **Uptime Kuma** — external uptime + **TLS-certificate-expiry** monitoring, one
  monitor per Mascope server. Complements the healthchecks.io dead-man's-switch
  checks (backups, disk) with "is the site actually reachable / is the cert about
  to expire".

These files are a **template**: copy them to the box and run them there. The real
`glitchtip.env` and `data/` never live in git.

> Everything published is bound to `192.168.1.88` only. If the box's LAN address
> differs, change it in both `compose.yaml` files (and the `ufw` rules below).

## 1. Prerequisites — Docker

```sh
# Docker Engine + compose plugin (skip if already installed). Review before
# running on a shared box.
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"      # log out/in for the group to take effect
docker --version && docker compose version
```

## 2. Firewall (LAN-only)

`ufw` alone does **not** filter Docker-published ports (Docker's DNAT runs before
`ufw`'s INPUT chain). Two layers, do both:

1. The `compose.yaml` files already bind published ports to `192.168.1.88` — they
   listen only on the LAN interface, not `0.0.0.0`.
2. Host firewall + a `DOCKER-USER` backstop via [ufw-docker](https://github.com/chaifeng/ufw-docker):

```sh
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 192.168.1.0/24 to any port 22   proto tcp   # SSH
sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp   # GlitchTip
sudo ufw allow from 192.168.1.0/24 to any port 3001 proto tcp   # Uptime Kuma
sudo ufw enable

sudo wget -O /usr/local/bin/ufw-docker \
  https://github.com/chaifeng/ufw-docker/raw/master/ufw-docker
sudo chmod +x /usr/local/bin/ufw-docker
sudo ufw-docker install
sudo systemctl restart ufw
sudo ufw route allow proto tcp from 192.168.1.0/24 to any port 8000
sudo ufw route allow proto tcp from 192.168.1.0/24 to any port 3001
```

## 3. GlitchTip

```sh
sudo mkdir -p /opt/glitchtip
sudo cp glitchtip/compose.yaml glitchtip/glitchtip.env.example /opt/glitchtip/
cd /opt/glitchtip
cp glitchtip.env.example glitchtip.env
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" glitchtip.env
docker compose up -d
docker compose logs -f web      # wait until it serves on :8000 (migrations run on boot); Ctrl-C when up
```

Then create the first account and a project (see [§6](#6-first-run-glitchtip)).

## 4. Uptime Kuma

```sh
sudo mkdir -p /opt/uptime-kuma/data
sudo cp uptime-kuma/compose.yaml /opt/uptime-kuma/
cd /opt/uptime-kuma
docker compose up -d
```

Open `http://192.168.1.88:3001` and create the admin account on first load
(see [§7](#7-uptime-kuma-monitors)).

## 5. Backups

Copy `backup-monitoring.sh` to the box (e.g. `/opt/monitoring/`), point it at your
restic repo, and schedule it nightly. It logically dumps GlitchTip's Postgres,
backs up GlitchTip uploads, and takes a quiesced copy of Uptime Kuma's SQLite.

```sh
sudo mkdir -p /opt/monitoring && sudo cp backup-monitoring.sh /opt/monitoring/
export RESTIC_REPOSITORY=/srv/restic-repo          # or your existing repo
sudo install -m 600 /dev/stdin /root/.restic-pass <<<"$(openssl rand -hex 24)"
sudo RESTIC_PASSWORD_FILE=/root/.restic-pass restic init --repo "$RESTIC_REPOSITORY"
```

Cron (niced so it never starves the backup workload):

```cron
RESTIC_REPOSITORY=/srv/restic-repo
RESTIC_PASSWORD_FILE=/root/.restic-pass
30 4 * * * nice -n 19 ionice -c3 /opt/monitoring/backup-monitoring.sh 2>&1 | logger -t monitoring-backup
```

## 6. First-run: GlitchTip

1. Browse to `http://192.168.1.88:8000` and **register the first account** at
   `/register` (allowed even with `ENABLE_USER_REGISTRATION=False`; there is no
   default admin). You are prompted to **create an organization**, then a
   **project** — pick platform **FastAPI**/**Python**.
2. **Copy the DSN.** Project → *Settings → Client Keys (DSN)*. It looks like
   `http://<public_key>@192.168.1.88:8000/<project_id>` (plain HTTP mirrors
   `GLITCHTIP_DOMAIN`, correct for this LAN).
3. **Notifications:** in the project/organization settings, add an alert (email
   via your SMTP relay, or a Slack/webhook integration) so new issues page you.

## 7. Turn on error reporting in Mascope

The backend has an **optional, off-by-default** GlitchTip sink (see
`docs/maintaining.md` → Monitoring). On each Mascope server:

1. Install the extra: `uv pip install "mascope_runtime[sentry]"` (or add the
   `sentry` extra to the backend image build).
2. Set the DSN in the **backend service environment only** (scopes reporting to
   the API server):
   ```sh
   MASCOPE_SENTRY_DSN=http://<public_key>@192.168.1.88:8000/<project_id>
   ```
3. Restart the backend. Smoke-test: `runtime.logger.error("glitchtip smoke test")`
   and confirm the event appears in GlitchTip. Unset the var anywhere you don't
   want reporting — it's a complete no-op when absent.

## 8. Uptime Kuma monitors

There is no supported config API, so add monitors in the UI. **For each Mascope
server:**

1. **Add New Monitor** → Type **HTTP(s)**.
2. **URL** = the server's **HTTPS** endpoint (e.g. `https://mascope-1.lan`).
   TLS-expiry checks require an `https://` target and *"Ignore TLS/SSL error"*
   **off**.
3. Set a friendly name, heartbeat interval, retries.
4. Enable **Certificate Expiry Notification** (global thresholds default to
   **21/14/7 days** before expiry).
5. Tick the notification channel (Settings → Notifications: email/Slack/webhook),
   then **Save**.

## Notes & caveats

- **GlitchTip 6** runs one all-in-one `web` container (no separate worker/beat).
  The in-container port var is `GRANIAN_PORT`, not `PORT`; to move the port, remap
  the host side in `compose.yaml`.
- **Postgres 18** stores data at `/var/lib/postgresql` (not `.../data`) — the
  volume mount reflects that. `POSTGRES_HOST_AUTH_METHOD=trust` is acceptable only
  because Postgres has no published port; set a password to harden.
- **`DOCKER-USER` interface**: if you hand-write firewall rules instead of
  ufw-docker, confirm the real interface with `ip -br addr` (often not `eth0`).
- **Resource footprint** on the shared box: budget ~1 GB RAM for GlitchTip
  (web + Postgres + Valkey) and ~256 MB for Uptime Kuma. Trim GlitchTip's worker
  with `VTASKS_CONCURRENCY` if constrained.
- Pin concrete image tags (`glitchtip/glitchtip:6.x`, `louislam/uptime-kuma:2.x.y`,
  `postgres:18.x`) before you consider this production-frozen.
