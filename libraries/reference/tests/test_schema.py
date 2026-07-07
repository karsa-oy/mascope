"""Guard the library's Core table handles against the backend ORM.

The physical tables are defined by the backend ORM models; this library
addresses them by column name. If the two drift, ingest/query break silently.
This test asserts parity - it is skipped in the isolated library environment
where the backend is not installed, and runs in the full workspace / CI.
"""

import pytest


pytest.importorskip("mascope_backend")

from mascope_backend.db.models import (  # noqa: E402
    ReferenceCompound,
    ReferenceSource,
)
from mascope_reference.schema import (  # noqa: E402
    reference_compound,
    reference_source,
)


def test_source_columns_match_orm():
    assert set(reference_source.c.keys()) == set(
        ReferenceSource.__table__.columns.keys()
    )


def test_compound_columns_match_orm():
    assert set(reference_compound.c.keys()) == set(
        ReferenceCompound.__table__.columns.keys()
    )
