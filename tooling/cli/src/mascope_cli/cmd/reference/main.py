"""
`mascope reference` - ingest and inspect mirrored public chemistry databases.

Fetches happen out of band; this command runs a source's ETL adapter over a
downloaded dump and upserts the normalized records into the ``reference_*``
tables as a versioned load, mirroring how the demo dataset is built and keeping
ingestion off the request path. Each load is versioned for reproducibility and
becomes the active version of its source.
"""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import create_engine, select
from sqlalchemy.pool import NullPool

from mascope_cli.runtime import runtime
from mascope_reference import available_sources, get_adapter, ingest
from mascope_reference.ingest import DEFAULT_BATCH_SIZE
from mascope_reference.schema import reference_source


reference_app = typer.Typer()
console = Console()


def _sync_engine():
    """Build a synchronous engine for the active runtime env's database.

    Mirrors ``mascope dev migrate`` - resolves the sync Postgres URL from the
    runtime config and the ``POSTGRES_PASSWORD_FILE`` secret.

    :raises typer.Exit: If the database is not configured.
    """
    db_cfg = runtime.full_config.backend.database
    if not db_cfg:
        runtime.logger.error("Database not configured in .mascope.toml")
        raise typer.Exit(1)
    password = runtime.secret("POSTGRES_PASSWORD_FILE", "postgres_password.txt")
    url = db_cfg.get_postgres_url_sync(password=password, env_name=runtime.env.name)
    return create_engine(url, poolclass=NullPool)


@reference_app.callback()
def main():
    """Ingest and inspect mirrored public chemistry databases."""


@reference_app.command("sources")
def sources() -> None:
    """List the reference sources with a registered ETL adapter."""
    for name in available_sources():
        adapter = get_adapter(name)
        console.print(f"[bold]{name}[/bold]  (license: {adapter.license})")


@reference_app.command()
def sync(
    source: Annotated[
        str,
        typer.Argument(help="Registered source name, e.g. 'pubchem' (see 'sources')."),
    ],
    path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Path to the downloaded source dump (.sdf/.csv/.xml, optionally .gz).",
        ),
    ],
    version: Annotated[
        str,
        typer.Option(
            "--version",
            "-v",
            help="Version tag for this load (release date/tag), for reproducibility.",
        ),
    ],
    batch_size: Annotated[
        int,
        typer.Option("--batch-size", help="Rows per bulk insert."),
    ] = DEFAULT_BATCH_SIZE,
    prune: Annotated[
        bool,
        typer.Option(
            "--prune",
            help="Delete prior (now inactive) loads of this source after success.",
        ),
    ] = False,
    stage: Annotated[
        bool,
        typer.Option(
            "--stage",
            help="Ingest without activating (does not replace the current version).",
        ),
    ] = False,
) -> None:
    """Ingest a source dump as a new versioned load."""
    try:
        adapter = get_adapter(source)
    except KeyError as error:
        runtime.logger.error(str(error))
        raise typer.Exit(1) from None

    engine = _sync_engine()
    runtime.logger.info(
        f"Ingesting '{source}' (version '{version}') from {path.name}..."
    )

    def _progress(count: int) -> None:
        runtime.logger.info(f"  ...{count:,} records ingested")

    try:
        result = ingest(
            engine,
            adapter,
            path,
            version,
            batch_size=batch_size,
            activate=not stage,
            prune=prune,
            progress=_progress,
        )
    finally:
        engine.dispose()

    runtime.logger.success(
        f"Ingested {result.ingested:,} records from '{result.source}' "
        f"(version '{result.version}', source_id={result.reference_source_id}, "
        f"{result.skipped:,} skipped)."
    )
    if stage:
        runtime.logger.info(
            "Load staged (inactive). Activation replaces the current version."
        )


@reference_app.command()
def status() -> None:
    """Show ingested sources and their versions from the database."""
    engine = _sync_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                select(
                    reference_source.c.name,
                    reference_source.c.version,
                    reference_source.c.license,
                    reference_source.c.record_count,
                    reference_source.c.is_active,
                    reference_source.c.ingested_at,
                ).order_by(
                    reference_source.c.name, reference_source.c.ingested_at.desc()
                )
            ).all()
    finally:
        engine.dispose()

    if not rows:
        runtime.logger.info("No reference sources ingested yet.")
        return

    table = Table(title="Reference sources")
    table.add_column("Source")
    table.add_column("Version")
    table.add_column("License")
    table.add_column("Records", justify="right")
    table.add_column("Active")
    table.add_column("Ingested (UTC)")
    for name, version, lic, count, is_active, ingested_at in rows:
        table.add_row(
            name,
            version,
            lic,
            f"{count:,}",
            "[green]yes[/green]" if is_active else "no",
            str(ingested_at),
        )
    console.print(table)
