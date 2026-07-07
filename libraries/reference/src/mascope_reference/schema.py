"""Lightweight Core table handles for the reference mirror.

The physical tables are *defined* by the backend ORM models (the single source
of truth for Alembic migrations and constraint naming). This module gives the
library its own column-name-only handles onto those same tables so the query
and ingest paths can build statements without importing the backend - the CLI
ingests and the backend queries through one shared column vocabulary.

The column names here MUST stay in lockstep with the backend ORM models; a
schema test asserts they do.
"""

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Boolean,
    Float,
    Integer,
    String,
    Text,
    column,
    table,
)


REFERENCE_SOURCE_TABLE = "reference_source"
REFERENCE_COMPOUND_TABLE = "reference_compound"


#: One row per ingested source + version (provenance, license, active flag).
reference_source = table(
    REFERENCE_SOURCE_TABLE,
    column("reference_source_id", Integer),
    column("name", String),
    column("version", String),
    column("license", String),
    column("record_count", Integer),
    column("is_active", Boolean),
    column("ingested_at", TIMESTAMP(timezone=True)),
)

#: One row per (compound, source version). ``xrefs`` is typed JSON so the dict
#: binds correctly on both Postgres (production) and SQLite (tests).
reference_compound = table(
    REFERENCE_COMPOUND_TABLE,
    column("reference_compound_id", Integer),
    column("reference_source_id", Integer),
    column("formula", String),
    column("monoisotopic_mass", Float),
    column("inchikey", String),
    column("name", Text),
    column("smiles", Text),
    column("inchi", Text),
    column("source_native_id", String),
    column("xrefs", JSON),
    column("license", String),
)

# Column-name lists reused by the ingest path (everything except the
# autoincrement primary key, which the database assigns).
SOURCE_INSERT_COLUMNS = (
    "name",
    "version",
    "license",
    "record_count",
    "is_active",
    "ingested_at",
)
COMPOUND_INSERT_COLUMNS = (
    "reference_source_id",
    "formula",
    "monoisotopic_mass",
    "inchikey",
    "name",
    "smiles",
    "inchi",
    "source_native_id",
    "xrefs",
    "license",
)
