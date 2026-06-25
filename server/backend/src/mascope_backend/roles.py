"""
Canonical role mapping: role name -> access level (used as the ``role_id``).

Kept deliberately secret-free and import-light so it can be imported both by the
auth config and by Alembic migrations. Migrations run in the ``db_init``
container, where only the postgres secret is mounted (not the JWT secret), so
this module (and its empty parent package ``__init__``) must never import
anything that reads a secret.
"""

ROLE_ACCESS_LEVELS: dict[str, int] = {
    "guest": 100,
    "editor": 200,
    "admin": 300,
    "owner": 400,
}
