#!/usr/bin/env bash
#
# Nightly Mascope backup — local dump layer + encrypted off-site copy.
#
# Layer 1 (local):   `mascope prod db backup create` dumps the active
#                    environment's database into .runtime/database/backups/prod/,
#                    then prunes dumps older than LOCAL_RETENTION_DAYS.
# Layer 2 (off-site): restic pushes the dump directory and the filestore to an
#                    encrypted repository (Hetzner Storage Box over SFTP,
#                    S3-compatible object storage, ...) and applies the
#                    KEEP_DAILY/KEEP_WEEKLY/KEEP_MONTHLY retention policy.
#
# Configuration lives in $MASCOPE_PATH/.runtime/secrets/backup.env
# (template: tooling/backup.env.example). Requires restic (installed by
# tooling/ubuntu.sh) and the mascope CLI.
#
# Cron example (see docs/dev/developer_guide.md, "Automated backups"):
#   0 4 * * * $MASCOPE_PATH/tooling/backup-cron.sh 2>&1 | logger -t mascope-backup

set -euo pipefail

log() { echo "[backup] $1"; }

# --- Configuration -----------------------------------------------------------

: "${MASCOPE_PATH:?MASCOPE_PATH must be set (add it to the crontab header)}"

CONFIG="${MASCOPE_BACKUP_ENV:-${MASCOPE_PATH}/.runtime/secrets/backup.env}"
if [[ ! -f "$CONFIG" ]]; then
    log "ERROR: config not found: $CONFIG (copy tooling/backup.env.example there)"
    exit 1
fi
# shellcheck source=backup.env.example
source "$CONFIG"

: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY must be set in backup.env}"
: "${RESTIC_PASSWORD:?RESTIC_PASSWORD must be set in backup.env}"
export RESTIC_REPOSITORY RESTIC_PASSWORD
# S3 credentials, if present in backup.env
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}" AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"

LOCAL_RETENTION_DAYS="${LOCAL_RETENTION_DAYS:-7}"
KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-4}"
KEEP_MONTHLY="${KEEP_MONTHLY:-6}"
DUMP_DIR="${MASCOPE_PATH}/.runtime/database/backups/prod"

# --- Failure alerting --------------------------------------------------------

# On any error, ping the /fail endpoint (healthchecks.io convention) so a
# silent cron failure still raises an alert. HEALTHCHECK_URL is optional.
on_error() {
    log "ERROR: backup failed (line $1)"
    if [[ -n "${HEALTHCHECK_URL:-}" ]]; then
        curl -fsS -m 10 --retry 3 "${HEALTHCHECK_URL}/fail" >/dev/null || true
    fi
    exit 1
}
trap 'on_error $LINENO' ERR

# The dump directory and pre-existing dumps are often root-owned (created by
# the docker daemon / init container), while this script typically runs as a
# regular user. Pruning needs write permission on the directory itself, so
# fail fast (and alert) instead of tracebacking halfway through.
if [[ -d "$DUMP_DIR" && ! -w "$DUMP_DIR" ]]; then
    log "ERROR: $DUMP_DIR is not writable by $(whoami) — pruning would fail."
    log "Fix once with: sudo chown -R $(whoami) $DUMP_DIR"
    false
fi

# --- Layer 1: local database dump -------------------------------------------

log "creating database dump..."
mascope prod db backup create --label cron
log "pruning local dumps older than ${LOCAL_RETENTION_DAYS} days..."
mascope prod db backup delete --retention-days "$LOCAL_RETENTION_DAYS"

# --- Layer 2: encrypted off-site copy ----------------------------------------

# Ensure the off-site repository exists before backing up. `restic cat config`
# is the existence probe, but it also fails on a transient connection blip
# (e.g. a flaky VPN) — so retry before concluding the repo is absent, and if we
# then init and restic reports the repo already exists, treat that as success.
# Without this, a single blip aborts the run AND wastes the dump just taken.
ensure_repo() {
    local attempt init_out
    for attempt in 1 2 3; do
        if restic cat config >/dev/null 2>&1; then
            return 0
        fi
        log "repository probe failed (attempt ${attempt}/3); retrying in 10s..."
        sleep 10
    done

    log "repository not reachable after 3 probes — attempting restic init..."
    if init_out=$(restic init 2>&1); then
        log "initialized a new restic repository"
        return 0
    fi
    if grep -qiE "already (exists|initialized)" <<<"$init_out"; then
        log "repository already exists; earlier probes failed transiently, proceeding"
        return 0
    fi
    log "ERROR: cannot reach or initialize the repository: ${init_out}"
    return 1
}

ensure_repo

BACKUP_PATHS=("$DUMP_DIR")
if [[ -n "${FILESTORE_PATH:-}" ]]; then
    BACKUP_PATHS+=("$FILESTORE_PATH")
else
    log "WARNING: FILESTORE_PATH not set — uploaded raw files are NOT backed up"
fi

log "pushing to off-site repository: ${BACKUP_PATHS[*]}"
restic backup --tag mascope-cron "${BACKUP_PATHS[@]}"

log "applying off-site retention (daily=${KEEP_DAILY} weekly=${KEEP_WEEKLY} monthly=${KEEP_MONTHLY})..."
restic forget --tag mascope-cron \
    --keep-daily "$KEEP_DAILY" \
    --keep-weekly "$KEEP_WEEKLY" \
    --keep-monthly "$KEEP_MONTHLY" \
    --prune

# Lightweight repository integrity check (metadata only, no data download).
restic check >/dev/null

# --- Success ------------------------------------------------------------------

if [[ -n "${HEALTHCHECK_URL:-}" ]]; then
    curl -fsS -m 10 --retry 3 "$HEALTHCHECK_URL" >/dev/null || true
fi
log "backup completed successfully"
