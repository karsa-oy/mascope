"""
CLI sub-applications for WAL and journal operations.

Provides typer sub-apps that can be included in the main CLI interface.
All operations use direct SQLite connections.
"""

import typer

from .direct import (
    check_wal_status,
    direct_wal_checkpoint,
    get_journal_mode,
    set_journal_mode,
)


# Create sub-applications
journal_app = typer.Typer(name="journal", help="Journal mode operations")
wal_app = typer.Typer(name="wal", help="WAL (Write-Ahead Logging) operations")


# Journal commands
@journal_app.command("status")
def journal_status_cmd():
    """Check current journal mode and basic database info."""
    get_journal_mode()


@journal_app.command("set")
def set_journal_mode_cmd(
    mode: str = typer.Argument(
        "wal",
        help="Journal mode to set",
        show_default=True,
    ),
):
    """Set journal mode (wal or delete)."""
    # Validation is done in set_journal_mode function
    set_journal_mode(mode)


# WAL commands
@wal_app.command("status")
def wal_status_cmd():
    """Check detailed WAL status including file sizes and checkpoint info."""
    check_wal_status()


@wal_app.command("checkpoint")
def wal_checkpoint_cmd(
    mode: str = typer.Argument(
        "RESTART",
        help="Checkpoint mode (PASSIVE, FULL, RESTART, TRUNCATE)",
        show_default=True,
    ),
):
    """
    Execute WAL checkpoint operation.

    Modes:
    PASSIVE: Safe for concurrent operations (non-blocking).
    FULL: Blocks new writers, use for maintenance.
    RESTART: Ensures clean WAL state, blocks readers/writers.
    TRUNCATE: Aggressive mode that truncates WAL to 0 bytes.
    """
    direct_wal_checkpoint(mode.upper())
