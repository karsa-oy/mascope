"""
Tests for the JSON sanitation of the sample-file peaks payload.

Peak arrays can legitimately carry NaN (quantities an instrument type does
not produce, e.g. TOF values for Orbitrap data), and strict JSON rejects
non-finite floats - a single NaN used to fail the whole peaks response.
"""

import json
import math

from mascope_backend.api.controllers.sample.files.sample_files_controller import (
    finite_or_none,
)


class TestFiniteOrNone:
    def test_non_finite_values_become_none(self):
        values = [1.5, float("nan"), 2.5, float("inf"), float("-inf")]

        assert finite_or_none(values) == [1.5, None, 2.5, None, None]

    def test_finite_values_and_none_pass_through(self):
        values = [0.0, -3.25, None, 7e300]

        assert finite_or_none(values) == values

    def test_empty_list(self):
        assert finite_or_none([]) == []

    def test_result_is_strict_json_serializable(self):
        payload = finite_or_none([100.1, math.nan, math.inf])

        # allow_nan=False mirrors the strict encoder the API response uses.
        assert json.dumps(payload, allow_nan=False) == "[100.1, null, null]"
