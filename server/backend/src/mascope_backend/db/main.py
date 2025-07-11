from typing import Annotated
import typer

from mascope_backend.db.ops.backup import run_db_backup
from mascope_backend.db.ops.clean_access_tokens import run_db_clean_access_tokens
from mascope_backend.db.ops.create_database import run_db_create
from mascope_backend.db.ops.filestore import ACTIONS, run_action
from mascope_backend.db.ops.restore import run_db_restore
from mascope_backend.db.ops.maintenance import run_db_maintenance
from mascope_backend.db.wal.cli import journal_app, wal_app

db_app = typer.Typer()

# Register the sub-apps
db_app.add_typer(journal_app)
db_app.add_typer(wal_app)


@db_app.callback()
def main():
    """
    Manage mascope SQLite database
    """


@db_app.command()
def create():
    """
    Create a Mascope database.
    """
    run_db_create()


@db_app.command()
def backup():
    """
    Create a backup of the SQLite database.
    """
    run_db_backup()


@db_app.command()
def restore(
    tables: list[str] | None = typer.Argument(
        None,
        help="Tables to restore. If not provided, all configured tables will be restored.",
    )
):
    """
    Restore a Mascope database.

    Optionally specify tables to restore (e.g., mascope-db restore sample_file sample_item).
    """
    run_db_restore(tables)


@db_app.command()
def maintenance():
    """
    Execute database maintenance.
    """
    run_db_maintenance()


@db_app.command()
def clean_tokens():
    """
    Clean access tokens in the database.
    """
    run_db_clean_access_tokens()


def complete_filestore_action() -> list[str]:
    """Autocomplete the filestore action argument.

    :return: List of available filestore actions.
    :rtype: list[str]
    """
    return [a for a in ACTIONS.keys()]


@db_app.command()
def filestore(
    action: Annotated[
        str,
        typer.Argument(
            help="The filestore action to perform",
            autocompletion=complete_filestore_action,
        ),
    ],
):
    """
    Perform actions to all files in the filestore
    """
    run_action(action)


def exec():
    db_app()


if __name__ == "__main__":
    exec()
