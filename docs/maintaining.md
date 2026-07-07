# Maintaining a Mascope deployment

The operator runbook for a self-hosted production server: how it is provisioned,
how it starts, how it updates, how it is backed up, and where to look when
something is off. For internals see
[developer_guide.md](dev/developer_guide.md); for the customer-facing hosting
overview see [hosting.md](hosting.md).

Everything below assumes an Ubuntu host provisioned with
[`tooling/ubuntu.sh`](../tooling/ubuntu.sh).

## At a glance

| Task | Command |
|---|---|
| Find the deployment path | `mascope path` |
| Start / stop the stack | `mascope prod up --detach` / `mascope prod down` |
| Container status / logs | `mascope prod ps` / `mascope prod logs --follow` |
| **Check for an update (applies nothing)** | `mascope prod update --check` |
| Update now | `mascope prod update` |
| Approve / defer a pending migration update | `mascope prod update --confirm` / `--snooze 7` |
| Enable unattended updates | edit `/etc/mascope/update.env`, then `sudo systemctl enable --now mascope-update.timer` |
| Update history | `cat "$(mascope path)/.runtime/update/status.log"` |
| Back up now | `mascope prod db backup create` |

## Provisioning

```sh
git clone git@github.com:karsa-oy/mascope.git && cd mascope
./tooling/ubuntu.sh install
```

`ubuntu.sh` installs system dependencies (Docker, uv, Node, restic, jemalloc,
...), builds the `mascope` binary, writes `MASCOPE_PATH` to `/etc/environment`,
and installs the systemd units (below). Re-run with `reinstall` after pulling
new tooling, or `uninstall` to remove the binary and units.

> The provisioning user is the deploy user. `mascope.service` and
> `mascope-update.service` run as that user and read `MASCOPE_PATH` /
> `LD_PRELOAD` from `/etc/environment`.

## The stack (boot service)

`mascope.service` brings the stack up on boot and down on shutdown:

```sh
sudo systemctl status mascope.service
sudo systemctl restart mascope.service     # = mascope prod down && up
```

Day to day you can also drive it directly:

```sh
mascope prod up --detach       # start (db_init runs pending migrations first)
mascope prod ps                # container status
mascope prod logs --follow backend
mascope prod restart backend
mascope prod down
```

## Updating

A release is either a **fast update** (new container images, no schema change,
near-zero downtime) or a **migration update** (a database migration runs on
startup and causes a short outage). The tooling tells the two apart so you only
schedule downtime when it is real.

### Preflight - know before you apply

```sh
mascope prod update --check        # classify the pending update, change nothing
mascope prod update --check --json # machine-readable
```

Outcome (also the exit code): `up-to-date` (0), `fast-update` (10),
`migration-update` (20), error (2).

### Manual update

```sh
mascope prod update                  # move to the latest release
mascope prod update --version v1.3.0 # move to a specific release
```

This pulls the target images and does a rolling restart. Database migrations run
automatically on startup; `db_init` takes a **pre-migration dump** into
`.runtime/database/backups/prod/` first. A failed image pull aborts before the
running stack is touched. (You do **not** need `mascope prod down` first - that
only adds downtime.)

### Unattended updates (the timer)

`mascope-update.timer` runs `mascope prod update --auto` nightly. It is
installed **disabled**. `--auto` automatically tracks the newest GitHub
**release tag** (`vX.Y.Z`) - there is no version to pin by hand. To turn it on:

1. Make sure the stack is running - the applied database revision is read from
   the live Postgres container. **No credentials are needed**: `--auto` reads
   the public GitHub releases API over plain HTTPS.
2. Enable the timer (adjust the window / grace first if you like):

   ```sh
   sudoedit /etc/mascope/update.env      # optional: MASCOPE_UPDATE_WINDOW, grace
   sudo systemctl enable --now mascope-update.timer
   ```

Each run:

- **Up to date** -> nothing.
- **Fast update** -> applied inside the maintenance window
  (`MASCOPE_UPDATE_WINDOW`, e.g. `2-5`), then health-checked. A failed health
  check **alerts and stops - it never rolls back automatically** (see
  Troubleshooting).
- **Migration update** -> recorded and reported (exit 30), then applied at the
  next window once its grace period elapses (`MASCOPE_UPDATE_GRACE_DAYS`,
  default 7 days) **or** you confirm it - unless it has been snoozed.

Steer a pending migration update:

```sh
mascope prod update --confirm    # apply at the next window, skip the grace wait
mascope prod update --snooze 7   # postpone 7 days
```

Configuration lives in `/etc/mascope/update.env` (`MASCOPE_UPDATE_WINDOW`,
`MASCOPE_UPDATE_GRACE_DAYS`, `MASCOPE_UPDATE_REPO`). Observe activity:

```sh
systemctl list-timers mascope-update.timer
journalctl -u mascope-update.service
cat "$(mascope path)/.runtime/update/status.log"   # applied / pending history
cat "$(mascope path)/.runtime/update/state.json"   # the current pending update
```

## Backups

[`tooling/backup-cron.sh`](../tooling/backup-cron.sh) runs a two-layer nightly
backup: a local database dump (`mascope prod db backup create`, pruned by
`LOCAL_RETENTION_DAYS`) plus an encrypted off-site copy of the dumps and
filestore via [restic](https://restic.net/).

Set it up:

1. Copy the template and fill it in (restic repo + password, retention):

   ```sh
   cp tooling/backup.env.example "$(mascope path)/.runtime/secrets/backup.env"
   sudoedit "$(mascope path)/.runtime/secrets/backup.env"
   ```

2. Add a crontab entry (the header must export `MASCOPE_PATH`):

   ```cron
   MASCOPE_PATH=/path/to/mascope
   0 4 * * * $MASCOPE_PATH/tooling/backup-cron.sh 2>&1 | logger -t mascope-backup
   ```

Restore a dump into the active environment:

```sh
mascope prod db backup list
mascope prod db restore <dump-file> --yes    # or omit the file for the latest
```

## Files and secrets

| Path | What |
|---|---|
| `/etc/environment` | `MASCOPE_PATH`, `LD_PRELOAD` (read by the systemd units) |
| `/etc/mascope/update.env` | update window / grace / repo (chmod 600) |
| `$MASCOPE_PATH/.runtime/secrets/` | `postgres_password.txt`, `jwt_secret_key.txt`, `server_owner_secret_key.txt`, TLS cert/key, `backup.env` |
| `$MASCOPE_PATH/.runtime/database/backups/prod/` | database dumps (incl. pre-migration) |
| `$MASCOPE_PATH/.runtime/update/` | `state.json` (pending update), `status.log` |

## Troubleshooting

**Stack won't start.** `sudo systemctl status mascope.service`, then
`mascope prod ps` and `mascope prod logs backend`. Confirm Docker is up and the
secrets in `.runtime/secrets/` exist.

**Update timer never fires / always fails.** `systemctl list-timers` to confirm
it is enabled; `journalctl -u mascope-update.service` for the reason. Exit 2 is
usually a stack that is down (the DB revision is read from the running Postgres)
or no network to reach the releases API. Exit 30 is *not* a failure - it means a
migration update is pending.

**A migration update won't apply.** It waits for the maintenance window, the
grace period, or a confirm, and never applies while snoozed. Run
`mascope prod update --check` to see the classification and
`cat "$(mascope path)/.runtime/update/state.json"` for its `first_seen_at` /
`snooze_until` / `confirmed` state. `mascope prod update --confirm` applies it at
the next window.

**Backend unhealthy after an update.** The updater stops and leaves the stack in
place (no automatic rollback). Investigate with `mascope prod logs backend`. To
roll back manually: if a migration ran, first restore the pre-migration dump
(`mascope prod db backup list`, then `mascope prod db restore <dump> --yes`),
then redeploy the previous release with
`mascope prod update --version v<previous>`.
