"""Versioned ingest tests against a SQLite mirror."""

from pathlib import Path

from sqlalchemy import func, select

from mascope_reference.adapters.pubchem import PubChemAdapter
from mascope_reference.ingest import ingest
from mascope_reference.schema import reference_compound, reference_source


SDF_TWO = """> <PUBCHEM_COMPOUND_CID>
962

> <PUBCHEM_MOLECULAR_FORMULA>
H2O

> <PUBCHEM_IUPAC_INCHIKEY>
XLYOFNOQVPJJNP-UHFFFAOYSA-N

$$$$
> <PUBCHEM_COMPOUND_CID>
2244

> <PUBCHEM_MOLECULAR_FORMULA>
C9H8O4

> <PUBCHEM_IUPAC_INCHIKEY>
BSYNRYMUTXBXSQ-UHFFFAOYSA-N

$$$$
"""

# One good record and one whose formula has no parseable elements (dropped).
SDF_WITH_BAD = """> <PUBCHEM_COMPOUND_CID>
1

> <PUBCHEM_MOLECULAR_FORMULA>
CH4

$$$$
> <PUBCHEM_COMPOUND_CID>
2

> <PUBCHEM_MOLECULAR_FORMULA>
+

$$$$
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_ingest_loads_records_and_records_source(sync_engine, tmp_path):
    path = _write(tmp_path, "pubchem.sdf", SDF_TWO)
    result = ingest(sync_engine, PubChemAdapter(), path, version="2026-07")

    assert result.ingested == 2
    assert result.skipped == 0

    with sync_engine.connect() as conn:
        count = conn.execute(
            select(func.count()).select_from(reference_compound)
        ).scalar()
        assert count == 2
        source = conn.execute(select(reference_source)).one()
        assert source.name == "pubchem"
        assert source.version == "2026-07"
        assert source.record_count == 2
        assert source.is_active is True
        # Formula was canonicalized and mass computed on ingest.
        water = conn.execute(
            select(reference_compound).where(
                reference_compound.c.source_native_id == "962"
            )
        ).one()
        assert water.formula == "H2O"
        assert water.monoisotopic_mass is not None


def test_ingest_skips_unusable_formula(sync_engine, tmp_path):
    path = _write(tmp_path, "bad.sdf", SDF_WITH_BAD)
    result = ingest(sync_engine, PubChemAdapter(), path, version="v1")
    assert result.ingested == 1
    assert result.skipped == 1


def test_reingest_deactivates_prior_version(sync_engine, tmp_path):
    path = _write(tmp_path, "pubchem.sdf", SDF_TWO)
    ingest(sync_engine, PubChemAdapter(), path, version="v1")
    ingest(sync_engine, PubChemAdapter(), path, version="v2")

    with sync_engine.connect() as conn:
        sources = conn.execute(
            select(reference_source.c.version, reference_source.c.is_active).order_by(
                reference_source.c.reference_source_id
            )
        ).all()
    assert sources == [("v1", False), ("v2", True)]


def test_reingest_with_prune_drops_prior_version(sync_engine, tmp_path):
    path = _write(tmp_path, "pubchem.sdf", SDF_TWO)
    ingest(sync_engine, PubChemAdapter(), path, version="v1")
    ingest(sync_engine, PubChemAdapter(), path, version="v2", prune=True)

    with sync_engine.connect() as conn:
        versions = conn.execute(
            select(reference_source.c.version)
        ).scalars().all()
        # Only the current version remains; compounds all point at it.
        assert versions == ["v2"]
        distinct_sources = conn.execute(
            select(func.count(func.distinct(reference_compound.c.reference_source_id)))
        ).scalar()
        assert distinct_sources == 1


def test_stage_does_not_activate(sync_engine, tmp_path):
    path = _write(tmp_path, "pubchem.sdf", SDF_TWO)
    ingest(sync_engine, PubChemAdapter(), path, version="v1")
    ingest(sync_engine, PubChemAdapter(), path, version="v2")
    # A staged load must not flip the current active version.
    ingest(sync_engine, PubChemAdapter(), path, version="v3", activate=False)

    with sync_engine.connect() as conn:
        active = conn.execute(
            select(reference_source.c.version).where(
                reference_source.c.is_active.is_(True)
            )
        ).scalars().all()
    assert active == ["v2"]


def test_source_name_override_lets_loads_coexist(sync_engine, tmp_path):
    # Two loads of the same adapter under different provenance names must not
    # deactivate each other - both stay active as distinct sources.
    path = _write(tmp_path, "pubchem.sdf", SDF_TWO)
    r1 = ingest(sync_engine, PubChemAdapter(), path, version="1", source_name="list-a")
    r2 = ingest(sync_engine, PubChemAdapter(), path, version="1", source_name="list-b")
    assert r1.source == "list-a" and r2.source == "list-b"

    with sync_engine.connect() as conn:
        active = conn.execute(
            select(reference_source.c.name)
            .where(reference_source.c.is_active.is_(True))
            .order_by(reference_source.c.name)
        ).scalars().all()
    assert active == ["list-a", "list-b"]
