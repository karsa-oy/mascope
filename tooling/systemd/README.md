# Unattended updates (systemd)

These units run `mascope prod update --auto` on a schedule so a Mascope server
keeps itself current without manual coordination.

What `--auto` does each run:

- **Up to date** - nothing happens.
- **Fast update** (new images, no database migration) - applied inside the
  maintenance window (`MASCOPE_UPDATE_WINDOW`), then health-checked. On a failed
  health check it alerts and stops; it never rolls back automatically.
- **Migration update** (causes downtime) - recorded and reported (exit code
  30). It is applied automatically at the next maintenance window once its
  grace period elapses (`MASCOPE_UPDATE_GRACE_DAYS`, default 7) or an operator
  confirms it, and provided it has not been snoozed. On a failed health check
  it alerts and stops (no auto-rollback).

An operator can steer a pending migration update:

```sh
mascope prod update --confirm      # apply at the next window (skip the grace wait)
mascope prod update --snooze 7     # postpone it 7 more days
```

## Install

1. Edit `mascope-update.service`: set `User`, `WorkingDirectory`, `MASCOPE_PATH`,
   the `MASCOPE_UPDATE_WINDOW`, and provide release read access (a `GH_TOKEN` or
   `gh auth login` for the service user). The server must be pinned to release
   tags (`vX.Y.Z`), which is the channel `--auto` tracks.
2. Copy both units into place and enable the timer:

   ```sh
   sudo cp mascope-update.service mascope-update.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now mascope-update.timer
   ```

3. Inspect activity:

   ```sh
   systemctl list-timers mascope-update.timer
   journalctl -u mascope-update.service
   cat "$MASCOPE_PATH/.runtime/update/status.log"   # applied / pending history
   ```

A recorded pending migration update lives at
`$MASCOPE_PATH/.runtime/update/state.json`.
