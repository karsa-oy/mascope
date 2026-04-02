"""Alembic migration environment - Mascope database migrations

Configures Alembic for PostgreSQL schema management using Mascope runtime config.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from mascope_backend.db.models import Base
from mascope_backend.db.secrets import postgres_password
from mascope_backend.runtime import runtime


# --- Module-level configuration ---
config = context.config  # Alembic config from alembic.ini
db_cfg = runtime.config.database  # Mascope database config
target_metadata = Base.metadata  # SQLAlchemy models metadata ('autogenerate' support)
url = db_cfg.get_postgres_url_sync(
    password=postgres_password, env_name=runtime.env.name
)  # PostgreSQL sync URL

# Interpret the config file for Python logging (sets up loggers basically).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL output to stdout).

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    Generates SQL migration scripts without executing them.
    Useful for review or manual execution on production databases.
    """
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (execute against database).

    Creates engine and executes migrations against live database.
    This is the standard mode for applying schema changes.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
