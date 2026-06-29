#!/usr/bin/env bash
# Database initialization for Mascope production environment.
#
# This script is designed to run as an init container in Docker Compose.
#   - Waits for PostgreSQL to be ready
#   - Creates the active env-specific database if it doesn't exist (first run in env)
#   - Checks for pending Alembic migrations
#   - Applies migrations if needed
#
# Environment variables required:
#   MASCOPE_DB_NAME - Target database name (e.g., mascope_test_env)
#   MASCOPE_DB_USER - PostgreSQL user (e.g., mascope_user)
#   MASCOPE_ENV     - Runtime environment name (e.g., test-env, default, etc.)
#   POSTGRES_PASSWORD_FILE - Path to postgres password secret file
#
# Secrets required:
#   /run/secrets/postgres_password - PostgreSQL password (mounted by Docker)
#
# Usage:
#   This script should NOT be run manually. It is automatically executed
#   by the db_init service in docker-compose.yaml during container startup.
#   The script uses pre-installed tools from the Docker image at:
#   /root/.local/share/uv/tools/mascope/bin/

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# --------- Validate environment variables ---------
if [[ -z "${MASCOPE_DB_NAME:-}" ]]; then
    log_error "MASCOPE_DB_NAME not set"
    exit 1
fi

if [[ -z "${MASCOPE_DB_USER:-}" ]]; then
    log_error "MASCOPE_DB_USER not set"
    exit 1
fi

if [[ -z "${MASCOPE_ENV:-}" ]]; then
    log_error "MASCOPE_ENV not set"
    exit 1
fi

if [[ -z "${POSTGRES_PASSWORD_FILE:-}" ]]; then
    log_error "POSTGRES_PASSWORD_FILE not set"
    exit 1
fi


# --------- Load PostgreSQL password from secret ---------
if [[ ! -f "${POSTGRES_PASSWORD_FILE}" ]]; then
    log_error "Password secret not found at ${POSTGRES_PASSWORD_FILE}"
    exit 1
fi

export PGPASSWORD
PGPASSWORD=$(cat "${POSTGRES_PASSWORD_FILE}")

# PostgreSQL connection details
PGHOST="postgres"
PGUSER="${MASCOPE_DB_USER}"
PGDATABASE="postgres"  # Connect to default DB for admin tasks

# --------- Wait for PostgreSQL server ---------
log_info "Waiting for PostgreSQL server..."

MAX_WAIT=30
WAITED=0

until pg_isready -h "$PGHOST" -U "$PGUSER" -d postgres 2>&1; do
    if [[ $WAITED -ge $MAX_WAIT ]]; then
        log_error "PostgreSQL server not ready after ${MAX_WAIT}s"
        log_error "Attempting direct connection test..."
        psql -h "$PGHOST" -U "$PGUSER" -d postgres -c "SELECT 1" 2>&1 || true
        exit 1
    fi
    
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

log_info "PostgreSQL server is ready"

# --------- Check and create database ---------
log_info "Checking database '${MASCOPE_DB_NAME}'..."

DB_EXISTS=$(psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -tAc \
    "SELECT 1 FROM pg_database WHERE datname='${MASCOPE_DB_NAME}'")

if [[ "$DB_EXISTS" == "1" ]]; then
    log_info "Database '${MASCOPE_DB_NAME}' exists"
else
    log_info "Creating database '${MASCOPE_DB_NAME}'..."
    
    if psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -c \
        "CREATE DATABASE \"${MASCOPE_DB_NAME}\"" > /dev/null; then
        log_info "Database '${MASCOPE_DB_NAME}' created successfully"
    else
        log_error "Failed to create database '${MASCOPE_DB_NAME}'"
        exit 1
    fi
fi


# --------- Run Alembic migrations ---------
log_info "Checking migrations..."

# Use the pre-installed alembic from uv tool environment (installed during docker build)
ALEMBIC_BIN="/root/.local/share/uv/tools/mascope/bin/alembic"

# Verify alembic binary exists
if [[ ! -x "$ALEMBIC_BIN" ]]; then
    log_error "alembic not found at $ALEMBIC_BIN"
    log_error "Available tools:"
    ls -la /root/.local/share/uv/tools/mascope/bin/ || true
    exit 1
fi

# Change to backend directory (required for alembic.ini)
cd /app/server/backend || {
    log_error "Failed to change directory to /app/server/backend"
    exit 1
}

# Get head revision from migration files.
# Capture combined stdout+stderr so that if alembic fails to load (e.g. a
# broken env.py or migration import), the real error is surfaced instead of a
# silent exit. Without this, `set -euo pipefail` aborts on the failing pipeline
# before the empty-check below ever runs, and `2>/dev/null` hides the cause.
if ! ALEMBIC_HEADS_OUTPUT=$("$ALEMBIC_BIN" heads 2>&1); then
    log_error "Failed to run 'alembic heads':"
    log_error "${ALEMBIC_HEADS_OUTPUT}"
    exit 1
fi

# `|| true` keeps pipefail from aborting when grep finds nothing; the
# empty-check below then reports it with the full alembic output for context.
HEAD_REV=$(echo "${ALEMBIC_HEADS_OUTPUT}" | grep -oE '[a-f0-9]{12}' | head -n1 || true)
if [[ -z "$HEAD_REV" ]]; then
    log_error "Could not parse head revision from 'alembic heads' output:"
    log_error "${ALEMBIC_HEADS_OUTPUT}"
    exit 1
fi

# Get current revision from database
CURRENT_REV=$(psql -h "$PGHOST" -U "$PGUSER" -d "$MASCOPE_DB_NAME" -tAc \
    "SELECT version_num FROM alembic_version LIMIT 1" 2>/dev/null || echo "none")

# Compare revisions
if [[ "$CURRENT_REV" == "$HEAD_REV" ]]; then
    log_info "Database up to date"
    log_info "Current revision: ${CURRENT_REV}"
elif [[ "$CURRENT_REV" == "none" ]] || [[ -z "$CURRENT_REV" ]]; then
    log_warn "No migration applied yet"
    log_info "Target revision: ${HEAD_REV}"
    log_info "Applying migrations..."
    
    if "$ALEMBIC_BIN" upgrade head 2>&1; then
        log_info "✅ Migrations applied successfully"
        log_info "Current revision: ${HEAD_REV}"
    else
        log_error "Migration failed"
        exit 1
    fi
else
    log_warn "Pending migrations detected"
    log_info "Current revision: ${CURRENT_REV}"
    log_info "Target revision:  ${HEAD_REV}"

    # --------- Pre-migration backup ---------
    # Only taken when actual migrations are pending on a non-empty database.
    # pg_dump runs inside this init container as root
    BACKUP_DIR="/backups"
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="${BACKUP_DIR}/${MASCOPE_DB_NAME}_${TIMESTAMP}_pre-migration.dump"
 
    log_info "Creating pre-migration backup..."
 
    # pg_dump connects directly over the compose network — no docker exec needed.
    # PGPASSWORD is already exported above. Custom format (-Fc) matches the
    # format produced by the CLI's pg_dump wrapper in admin.py, so dumps are
    # interchangeable with mascope prod db backup list / restore.
    if pg_dump \
        -h "$PGHOST" \
        -U "$PGUSER" \
        --format=custom \
        --no-owner \
        --no-acl \
        --file="$BACKUP_FILE" \
        "$MASCOPE_DB_NAME" 2>&1; then
 
        log_info "Pre-migration backup created: $(basename "$BACKUP_FILE")"
 
        # Init container runs as root; chown to the owner of the /backups mount
        # so the host user (and CLI) can manage the file without sudo.
        MOUNT_OWNER=$(stat -c '%u:%g' "$BACKUP_DIR")
        chown "$MOUNT_OWNER" "$BACKUP_FILE"
        log_info "Chowned backup to ${MOUNT_OWNER}"
    else
        log_error "Pre-migration backup failed — aborting to protect data"
        rm -f "$BACKUP_FILE"
        exit 1
    fi

    log_info "Applying migrations..."
    
    if "$ALEMBIC_BIN" upgrade head 2>&1; then
        log_info "✅ Migrations applied successfully"
        log_info "Current revision: ${HEAD_REV}"
    else
        log_error "Migration failed"
        exit 1
    fi
fi

log_info "✅ Database initialization complete"