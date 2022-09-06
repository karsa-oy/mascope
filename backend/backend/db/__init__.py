from backend.db.id import *  # noqa

import os
import re
import traceback
from importlib import import_module

# env vars
data_dir = os.environ.get('MASCOPE_PRIVATE_DATADIR')
db_dir = os.path.join(data_dir, 'database')


def run():
    try:
        print("Initializing mascope database")
        target_version = int(os.environ.get('MASCOPE_PUBLIC_DB_VERSION'))
        current_version = get_current_db_version()
        available_version = get_available_db_version()
        print(f"Detected mascope database version: v{current_version}")
        if target_version > available_version:
            raise ValueError(f"""
                Latest available version is: {available_version}.
            """)
        if current_version == target_version:
            print("No database migration needed.")
        else:
            print(f"This version of mascope requires: v{target_version}")
            current_version = migrate(current_version, target_version)
        # load api
        import_module('backend.api')
    except Exception as error:  # noqa
        traceback.print_exc()


def migrate(current_version, target_version):
    print("Executing migration pathway")
    if current_version == 0 and not os.path.exists(db_dir):
        os.mkdir(db_dir)
    while current_version < target_version:
        next_version = current_version + 1
        try:
            migration = import_module(f"backend.db.migration.v{next_version}")
        except Exception as error:
            traceback.print_exc()
            print(error)
        migration_label = f"from v{current_version} to v{next_version}"
        print(f"Attempting to migrate mascope database {migration_label}")
        try:
            migration.run()
        except Exception as error:
            print(f"Migration {migration_label} failed!")
            failed_db_path = os.path.join(
                db_dir, f"mascope.v{next_version}.db"
            )
            debug_db_path = os.path.join(
                db_dir, "mascope.debug.db"
            )
            if os.path.exists(failed_db_path):
                os.rename(failed_db_path, debug_db_path)
            traceback.print_exc()
            print(error)
            print(f"A copy failed target database is found at {debug_db_path}")
            raise RuntimeError('Database migration failed')
            break
        else:
            print(f"Migration {migration_label} succeded!")
            current_version = get_current_db_version()
    if current_version == target_version:
        print("Migration pathway succesful: database is now up-to-date.")
    return current_version


def get_available_db_version():
    migrations_dir = os.path.join(
        os.path.dirname(__file__), 'migration'
    )
    files = os.listdir(migrations_dir)
    migrations = [
        f for f in files
        if re.search('v[0-9]+.py', f)
    ]
    versions = [
        int(re.search('[0-9]+', migration).group())
        for migration in migrations
    ]
    return max(versions)


def get_current_db_version():
    v = 0
    if os.path.exists(db_dir):
        files = os.listdir(db_dir)
        databases = [
            f for f in files
            if re.search('mascope.v[0-9]+.db', f)
        ]
        versions = [
            int(re.search('[0-9]+', database).group())
            for database in databases
        ]
        if len(versions) > 0:
            v = max(versions)
    return v
