"""Unit tests for the per-ion isotope abundance threshold SQL expression."""

from sqlalchemy.dialects import postgresql

from mascope_backend.api.new.match.params.lib import (
    isotope_abundance_threshold_expr,
)
from mascope_backend.db import TargetIon


def _render(instrument: str, default: float) -> str:
    expr = isotope_abundance_threshold_expr(
        TargetIon.filter_params, instrument, default
    )
    return str(
        expr.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


class TestIsotopeAbundanceThresholdExpr:
    def test_coalesces_ion_override_with_default(self):
        sql = _render("Orbion", 1e-4)
        # Falls back to the instrument default when no ion override is present.
        assert "coalesce" in sql.lower()
        assert "0.0001" in sql

    def test_reads_override_keyed_by_instrument(self):
        sql = _render("Orbion", 1e-4)
        # Override is read from filter_params under the instrument key.
        assert "filter_params" in sql
        assert "Orbion" in sql
        assert "isotope_abundance_threshold" in sql
