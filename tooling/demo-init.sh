#!/usr/bin/env bash
# Demo loader for the containerized Mascope demo (docker-compose.demo.yaml).
#
# Runs as an init container in the published backend image (which bundles the
# full workspace + the mascope CLI + the postgres client). It prepares the
# `mascope_demo` database from the published demo bundle so the app comes up
# preloaded with real data and a ready-to-use login:
#   - writes throwaway local-only secret files the app reads on startup,
#   - waits for PostgreSQL,
#   - fetches + checksum-verifies the demo bundle from Zenodo (CLI registry),
#   - restores the snapshot database + filestore,
#   - upgrades the schema to head (in case the image is newer than the bundle),
#   - seeds the fixed demo credentials.
#
# Idempotent: a second `up` with the data already present skips the fetch +
# restore and only re-seeds (which is itself idempotent).
#
# Required environment (set by docker-compose.demo.yaml):
#   MASCOPE_ENV, MASCOPE_DB_NAME, MASCOPE_DB_USER, MASCOPE_DEMO_DB_PASSWORD,
#   MASCOPE_DEMO_JWT_SECRET, MASCOPE_DEMO_OWNER_SECRET

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

PGHOST="postgres"
PGUSER="${MASCOPE_DB_USER}"
DB="${MASCOPE_DB_NAME}"

# Mascope is installed as a uv tool, so its Python + entry points live in the
# tool venv (the same place db-init.sh finds alembic), not the base interpreter.
TOOL_BIN="/root/.local/share/uv/tools/mascope/bin"
PYTHON="$TOOL_BIN/python"
ALEMBIC_BIN="$TOOL_BIN/alembic"

# --- Write the local-only secret files the backend reads on startup ----------
# runtime.secret() resolves these from /app/.runtime/secrets/<name>.txt. The
# values are throwaway and for the localhost demo only - never reuse them.
SECRETS_DIR="/app/.runtime/secrets"
mkdir -p "$SECRETS_DIR"
printf '%s' "${MASCOPE_DEMO_DB_PASSWORD}" > "$SECRETS_DIR/postgres_password.txt"
printf '%s' "${MASCOPE_DEMO_JWT_SECRET}" > "$SECRETS_DIR/jwt_secret_key.txt"
printf '%s' "${MASCOPE_DEMO_OWNER_SECRET}" > "$SECRETS_DIR/server_owner_secret_key.txt"
log_info "Wrote demo secret files to $SECRETS_DIR"

export PGPASSWORD="${MASCOPE_DEMO_DB_PASSWORD}"

# --- Wait for PostgreSQL -----------------------------------------------------
log_info "Waiting for PostgreSQL server..."
MAX_WAIT=60
WAITED=0
until pg_isready -h "$PGHOST" -U "$PGUSER" -d postgres >/dev/null 2>&1; do
    if [[ $WAITED -ge $MAX_WAIT ]]; then
        log_error "PostgreSQL not ready after ${MAX_WAIT}s"
        exit 1
    fi
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done
log_info "PostgreSQL is ready"

# --- Skip if the demo data is already loaded (fast re-up) --------------------
# sample_item is a core table populated by the snapshot; a positive count means
# a previous run already restored the bundle into this database volume.
LOADED=$(psql -h "$PGHOST" -U "$PGUSER" -d "$DB" -tAc \
    "SELECT count(*) FROM sample_item" 2>/dev/null || echo "0")

if [[ "${LOADED//[[:space:]]/}" =~ ^[0-9]+$ ]] && [[ "${LOADED//[[:space:]]/}" -gt 0 ]]; then
    log_info "Demo data already present ($LOADED sample items); skipping restore"
else
    # --- Fetch + locate the published bundle (via the in-image CLI) ----------
    log_info "Fetching the demo bundle (downloads + checksum-verifies)..."
    "$PYTHON" -c "import os; os.environ['MASCOPE_ENV']='${MASCOPE_ENV}'; \
from mascope_cli.cmd.demo import _fetch; _fetch.fetch()"
    BUNDLE=$("$PYTHON" -c "from mascope_cli.cmd.demo import bundles; print(bundles.bundle_dir())")
    log_info "Bundle ready at $BUNDLE"

    DUMP="$BUNDLE/snapshot/mascope_demo.dump"
    if [[ ! -f "$DUMP" ]]; then
        log_error "Snapshot dump not found in bundle: $DUMP"
        exit 1
    fi

    # --- Restore the snapshot into a clean database -------------------------
    log_info "Recreating '$DB' and restoring the snapshot..."
    psql -h "$PGHOST" -U "$PGUSER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB\"" >/dev/null
    psql -h "$PGHOST" -U "$PGUSER" -d postgres -c "CREATE DATABASE \"$DB\"" >/dev/null
    pg_restore -h "$PGHOST" -U "$PGUSER" --no-owner --no-acl -d "$DB" "$DUMP"
    log_info "Snapshot restored into '$DB'"

    # --- Restore the filestore ---------------------------------------------
    FILESTORE_SRC="$BUNDLE/snapshot/filestore"
    FILESTORE_DST="/app/.runtime/env/${MASCOPE_ENV}/filestore"
    mkdir -p "$FILESTORE_DST"
    if [[ -d "$FILESTORE_SRC" ]]; then
        cp -a "$FILESTORE_SRC"/. "$FILESTORE_DST"/
        log_info "Filestore restored to $FILESTORE_DST"
    else
        log_warn "Bundle has no filestore tree at $FILESTORE_SRC; skipping"
    fi
fi

# --- Upgrade the schema to head (image may be newer than the snapshot) -------
cd /app/server/backend
log_info "Applying any pending migrations..."
"$ALEMBIC_BIN" upgrade head

# --- Seed the fixed demo credentials (idempotent) ----------------------------
log_info "Seeding demo credentials..."
"$PYTHON" -m mascope_backend.db.scripts.seed_demo

log_info "✅ Demo database ready"
