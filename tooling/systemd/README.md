# Mascope systemd units

The systemd units that run a Mascope deployment. `tooling/ubuntu.sh install`
templates and installs all of them (filling in the deploy user and the resolved
`mascope` binary); you normally don't touch them by hand. For the full
operations story see [docs/maintaining.md](../../docs/maintaining.md).

| File | Installed as | Enabled by `ubuntu.sh`? | Purpose |
|---|---|---|---|
| `mascope.service` | `mascope.service` | yes | Bring the stack up on boot (`prod up --detach`) / down on stop. |
| `mascope-update.service` | `mascope-update.service` | no (oneshot, run by the timer) | One unattended update pass (`prod update --auto`). |
| `mascope-update.timer` | `mascope-update.timer` | **no - opt-in** | Fire the update service nightly. |
| `update.env.example` | `/etc/mascope/update.env` (chmod 600) | seeded once | Update window / grace / release token. |

Both `.service` files template `@@USER@@` and `@@MASCOPE_BIN@@`; `MASCOPE_PATH`
and `LD_PRELOAD` come from `/etc/environment`, matching how `ubuntu.sh`
provisions the box.

## Enabling auto-updates

Auto-updates are installed **disabled** so a fresh server stays quiet until you
opt in. To turn them on, set a release token (the repo is private) in
`/etc/mascope/update.env`, then enable the timer:

```sh
sudoedit /etc/mascope/update.env          # set GH_TOKEN (and window/grace)
sudo systemctl enable --now mascope-update.timer
```

The server must be pinned to a release tag (`vX.Y.Z`) - the channel `--auto`
tracks.

## What each `--auto` run does

- **Up to date** - nothing.
- **Fast update** (new images, no migration) - applied inside the maintenance
  window (`MASCOPE_UPDATE_WINDOW`), then health-checked. A failed health check
  alerts and stops; it never rolls back automatically.
- **Migration update** (downtime) - recorded and reported (exit 30). Applied at
  the next window once the grace period elapses (`MASCOPE_UPDATE_GRACE_DAYS`,
  default 7) or an operator confirms it, unless snoozed.

Steer a pending migration update:

```sh
mascope prod update --check        # classify the pending update, apply nothing
mascope prod update --confirm      # apply at the next window (skip the grace wait)
mascope prod update --snooze 7     # postpone it 7 days
```

## Inspecting

```sh
systemctl list-timers mascope-update.timer
journalctl -u mascope-update.service
cat "$MASCOPE_PATH/.runtime/update/status.log"   # applied / pending history
cat "$MASCOPE_PATH/.runtime/update/state.json"   # the current pending update
```
