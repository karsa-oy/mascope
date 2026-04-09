"""
Database administration operations.

This package contains application-level data administration functions:
bulk updates, data sanitisation, ownership fixes, and similar one-off
or periodic data corrections that operate via SQLAlchemy sessions.

Distinction from other layers:

- Alembic migrations (`server/backend/alembic/versions/`): schema changes
  only — adding/removing tables and columns, changing constraints. Never touch
  data beyond what is structurally required. Run automatically on startup via
  the db-init container (prod) or `mascope dev migrate upgrade` (dev).

- `db/admin/` (this package): data manipulation against a stable schema.
  Functions here are imported by scripts in `db/scripts/` and exposed via
  `mascope dev db script` / `mascope prod db script`. No schema changes.

- `db/scripts/`: thin entry points that wire up the database engine,
  call functions from `db/admin/`, and report results. Intended for manual
  execution by developers — never called on app startup.
"""
