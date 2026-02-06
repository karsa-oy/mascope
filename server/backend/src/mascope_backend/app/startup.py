"""
Main process startup initialization.

This module contains one-time initialization logic that runs once
before the application starts accepting requests.

It handles tasks:
- Database migrations (schema changes)
- File system cleanup and setup
- Application state reset
"""

import os
import shutil

from mascope_backend.db import check_db_migration
from mascope_backend.runtime import runtime
from mascope_file.gc import gc_filestore


async def init_main_process():
    """
    Runs once per server startup, before any
    workers are spawned or requests are handled.

    Operations performed:
    - Database migrations (if needed)
    - Clean and recreate temporary file directory
    - Garbage collect orphaned files from filestore

    Does NOT configure database connections - each worker does that independently.

    :raises Exception: If any critical initialization step fails
    """
    db_cfg = runtime.config.database

    # Initialize database (includes migrations) if database is ready
    if db_cfg.type == "sqlite":
        runtime.logger.info("Main process: checking if database migrations are needed")
        await check_db_migration()

    # Reset temp directory
    runtime.logger.info("Main process: initializing temp directory")
    temp_dir = runtime.env.path("temp")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.mkdir(temp_dir)

    # Clean filestore
    runtime.logger.info("Main process: garbage collecting filestore")
    gc_filestore()
