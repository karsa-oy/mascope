import os
import re
import traceback
import shutil
import inspect
from datetime import datetime
from importlib import import_module

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from mascope_server.config import config

import mascope_runtime as runtime
logger = runtime.logger.service('backend')

def get_available_db_version():
    migrations_dir = os.path.join(os.path.dirname(__file__), "migration")
    files = os.listdir(migrations_dir)
    migrations = [f for f in files if re.search("v[0-9]+.py", f)]
    versions = [int(re.search("[0-9]+", migration).group()) for migration in migrations]
    return max(versions)


def get_current_db_version():
    v = 0
    if os.path.exists(config.server.database):
        files = os.listdir(config.server.database)
        databases = [f for f in files if re.search("mascope.v[0-9]+.db", f)]
        versions = [
            int(re.search("[0-9]+", database).group()) for database in databases
        ]
        if len(versions) > 0:
            v = max(versions)
    return v


def migrate(current_version, target_version):
    logger.info("Executing migration pathway")
    if current_version == 0 and not os.path.exists(config.server.database):
        os.mkdir(config.server.database)
    while current_version < target_version:
        next_version = current_version + 1
        try:
            migration = import_module(f"mascope_server.db.migration.v{next_version}")
        except Exception as error:
            logger.error(error)
        migration_label = f"from v{current_version} to v{next_version}"
        logger.info(f"Attempting to migrate mascope database {migration_label}")
        try:
            migration.run()
        except Exception as error:
            logger.error(f"Migration {migration_label} failed!")
            failed_db_path = os.path.join(config.server.database, f"mascope.v{next_version}.db")
            debug_db_path = os.path.join(config.server.database, "mascope.debug.db")
            if os.path.exists(failed_db_path):
                os.rename(failed_db_path, debug_db_path)
            logger.error(error)
            logger.error(f"A copy failed target database is found at {debug_db_path}")
            raise RuntimeError("Database migration failed")
            break
        else:
            logger.info(f"Migration {migration_label} succeded!")
            current_version = get_current_db_version()
    if current_version == target_version:
        logger.info("Migration pathway succesful: database is now up-to-date.")
    return current_version


async def test_database_connection():
    try:
        # create a new session and close it
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Database connection established successfully.")
    except Exception as e:
        logger.error("Error while establishing the database connection: ", e)


def create_db_backup(db_path, operation):
    """Creates a timestamped backup of the database."""
    data_path = os.path.dirname(db_path)
    current_version = get_current_db_version()
    backup_dir = os.path.join(data_path, "backup")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_db_path = os.path.join(
        backup_dir, f"{timestamp}_{operation}_backup_mascope.v{current_version}.db"
    )
    shutil.copyfile(db_path, backup_db_path)
    logger.info(f"Backup created at {backup_db_path}")
    return backup_db_path


async def run_migration_script(migration):
    """
    Executes a migration script, handling both synchronous and asynchronous run functions.
    """
    # Check if the migration's 'run' function is a coroutine
    if inspect.iscoroutinefunction(migration.run):
        # If it is a coroutine, await its execution
        logger.info("Running asynchronous migration script.")
        await migration.run()
    else:
        # Otherwise, run it as a synchronous function
        logger.info("Running synchronous migration script.")
        migration.run()


async def migrate(current_version, target_version):
    logger.info("Executing migration pathway")
    if current_version == 0 and not os.path.exists(db_dir):
        os.mkdir(db_dir)
    while current_version < target_version:
        next_version = current_version + 1
        try:
            migration = import_module(f"mascope_server.db.migration.v{next_version}")
        except Exception as error:
            logger.error(error)
        migration_label = f"from v{current_version} to v{next_version}"
        logger.info(f"Attempting to migrate mascope database {migration_label}")
        try:
            await run_migration_script(migration)
        except Exception as error:
            logger.error(f"Migration {migration_label} failed!")
            failed_db_path = os.path.join(db_dir, f"mascope.v{next_version}.db")
            debug_db_path = os.path.join(db_dir, "mascope.debug.db")
            if os.path.exists(failed_db_path):
                os.rename(failed_db_path, debug_db_path)
            logger.error(error)
            logger.error(f"A copy failed target database is found at {debug_db_path}")
            raise RuntimeError("Database migration failed")
        else:
            logger.info(f"Migration {migration_label} succeded!")
            current_version = get_current_db_version()
    if current_version == target_version:
        logger.info("Migration pathway succesful: database is now up-to-date.")
    return current_version


def configure_database_engine(version):
    db_path = os.path.join(db_dir, f"mascope.v{version}.db")

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,  # Check connection liveness before using a connection from the pool
        # echo=True, # TODO_debug_mode Enable logging of all SQL queries for debugging purposes
        connect_args={
            "timeout": 15
        },  # Set a timeout of 15 seconds for establishing connections and waiting for table locks
        future=True,  # Use future flag to enable 2.0 style
    )

    global ASYNC_SESSION
    ASYNC_SESSION = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Initialize global variables at module load
ASYNC_SESSION = None  # Global variable for session

db_dir = config.server.database


def async_session():
    return ASYNC_SESSION()


async def init_db():
    try:
        logger.info("Initializing mascope database")
        current_version = get_current_db_version()
        target_version = get_available_db_version()
        logger.info(f"Detected mascope database version: v{current_version}")
        if current_version == target_version:
            logger.info("No database migration needed.")
            configure_database_engine(current_version)
        else:
            logger.info(f"This version of mascope requires: v{target_version}")
            await migrate(current_version, target_version)
    except Exception as error:
        logger.error(error)
    await test_database_connection()


# env vars
current_version = get_current_db_version()
db_path = os.path.join(config.server.database, f"mascope.v{current_version}.db")

# Database configuration
DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Check connection liveness before using a connection from the pool
    # echo=True, # TODO_debug_mode Enable logging of all SQL queries for debugging purposes
    connect_args={
        "timeout": 15
    },  # Set a timeout of 15 seconds for establishing connections and waiting for table locks
)

async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
