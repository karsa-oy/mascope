#!/usr/bin/env bash
#
# Mascope disk-space monitor - alert before a full disk crashes the stack.
#
# A Mascope host writes to one or more filesystems that grow over time: the
# Postgres data, the filestore (uploaded raw files) and database dumps under
# $MASCOPE_PATH/.runtime, plus docker's image store. If any of them fills the
# disk, Postgres can wedge and the whole stack goes down. This check measures
# the free space on each and, when one drops below a floor, pings a
# healthchecks.io-style URL so a human is alerted with lead time to act.
#
# It is read-only: it never deletes anything. Run it from the systemd timer
# tooling/ubuntu.sh installs (mascope-disk-check.timer), or from cron:
#   */15 * * * * $MASCOPE_PATH/tooling/disk-check.sh 2>&1 | logger -t mascope-disk
#
# Configuration is all optional (template: tooling/disk-check.env.example). The
# systemd unit reads /etc/mascope/disk-check.env directly; when run standalone
# (e.g. from cron) this script instead sources
# $MASCOPE_PATH/.runtime/secrets/disk-check.env (override with
# MASCOPE_DISK_CHECK_ENV).

set -euo pipefail

log() { echo "[disk-check] $1"; }

: "${MASCOPE_PATH:?MASCOPE_PATH must be set (systemd reads it from /etc/environment)}"

# --- Configuration -----------------------------------------------------------

CONFIG="${MASCOPE_DISK_CHECK_ENV:-${MASCOPE_PATH}/.runtime/secrets/disk-check.env}"
if [[ -f "$CONFIG" ]]; then
    # shellcheck source=disk-check.env.example
    source "$CONFIG"
fi

# Absolute floor (GiB) and early-warning floor (percent of the filesystem).
# A path below EITHER is reported and alerts. Set MIN_FREE_PCT=0 to disable the
# percentage check (useful on very large disks where 10% is still plenty).
MIN_FREE_GB="${MIN_FREE_GB:-10}"
MIN_FREE_PCT="${MIN_FREE_PCT:-10}"
# Where docker stores image layers; override if your data-root is elsewhere.
DOCKER_ROOT="${DOCKER_ROOT:-/var/lib/docker}"

# --- Checks ------------------------------------------------------------------

problems=0
declare -A seen_mounts

check_path() {
    local label="$1" path="$2"

    # Resolve to the nearest existing ancestor: a not-yet-created directory
    # still lives on some filesystem whose free space we can measure.
    while [[ ! -e "$path" && "$path" != "/" ]]; do path="$(dirname "$path")"; done
    if [[ ! -e "$path" ]]; then
        log "skip ${label}: ${path} not found"
        return 0
    fi

    # df -P: one line per filesystem (no wrapping); -B1: sizes in bytes.
    local line mount size avail
    line="$(df -P -B1 "$path" | awk 'NR==2')"
    mount="$(awk '{print $6}' <<<"$line")"
    size="$(awk '{print $2}' <<<"$line")"
    avail="$(awk '{print $4}' <<<"$line")"

    # Guard against a malformed or zero-size df line (pseudo-filesystems) before
    # any arithmetic, so a weird mount can never crash the monitor.
    if ! [[ "$size" =~ ^[0-9]+$ && "$avail" =~ ^[0-9]+$ ]] || [[ "$size" -eq 0 ]]; then
        log "skip ${label} (${mount:-$path}): could not read filesystem size"
        return 0
    fi

    # One filesystem, one report (MASCOPE_PATH and docker often share a mount).
    if [[ -n "${seen_mounts[$mount]:-}" ]]; then
        return 0
    fi
    seen_mounts[$mount]=1

    # Pass values as awk variables and guard divisions with `if`: keeps the
    # arithmetic out of printf's argument list (a bare '>' there is parsed as
    # output redirection) and never divides by a zero-size pseudo-filesystem.
    local free_gb free_pct
    free_gb="$(awk -v a="$avail" 'BEGIN{ printf "%.1f", a/1073741824 }')"
    free_pct="$(awk -v s="$size" -v a="$avail" \
        'BEGIN{ if (s > 0) printf "%.0f", a*100/s; else printf "0" }')"

    local low=0
    if awk -v a="$avail" -v g="$MIN_FREE_GB" 'BEGIN{ exit !(a/1073741824 < g) }'; then
        low=1
    fi
    if [[ "${MIN_FREE_PCT}" -gt 0 ]] &&
        awk -v s="$size" -v a="$avail" -v p="$MIN_FREE_PCT" \
            'BEGIN{ exit !(s > 0 && a*100/s < p) }'; then
        low=1
    fi

    if [[ "$low" -eq 1 ]]; then
        log "LOW: ${label} (${mount}) has ${free_gb} GiB / ${free_pct}% free (floor ${MIN_FREE_GB} GiB / ${MIN_FREE_PCT}%)"
        problems=$((problems + 1))
    else
        log "ok:  ${label} (${mount}) has ${free_gb} GiB / ${free_pct}% free"
    fi
}

check_path "state (.runtime)" "$MASCOPE_PATH"
check_path "docker images" "$DOCKER_ROOT"

# --- Alerting ----------------------------------------------------------------

if [[ "$problems" -gt 0 ]]; then
    log "ALERT: ${problems} filesystem(s) below the free-space floor"
    if [[ -n "${HEALTHCHECK_URL:-}" ]]; then
        curl -fsS -m 10 --retry 3 "${HEALTHCHECK_URL}/fail" >/dev/null || true
    fi
    exit 1
fi

# All good - ping the success URL so a silently stalled monitor is itself
# noticed (healthchecks.io flags a check that stops reporting).
if [[ -n "${HEALTHCHECK_URL:-}" ]]; then
    curl -fsS -m 10 --retry 3 "$HEALTHCHECK_URL" >/dev/null || true
fi
log "ok: all monitored filesystems have enough free space"
