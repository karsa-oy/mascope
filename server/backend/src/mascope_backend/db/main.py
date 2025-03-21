import typer

from mascope_backend.db.ops.backup import run_db_backup
from mascope_backend.db.ops.clean_access_tokens import run_db_clean_access_tokens
from mascope_backend.db.ops.create_database import run_db_create
from mascope_backend.db.ops.restore import run_db_restore
from mascope_backend.db.ops.maintenance import run_db_maintenance

db_app = typer.Typer()


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
def restore():
    """
    Restore a Mascope database.
    """
    run_db_restore()


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


def exec():
    db_app()


if __name__ == "__main__":
    exec()
