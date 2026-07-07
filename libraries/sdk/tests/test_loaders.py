"""
Hermetic unit tests for the batch/sample name filtering in the high-level
loaders. These do not need a running stack.
"""

import inspect

import pandas as pd

from mascope_sdk import MascopeClient
from mascope_sdk._loaders import _name_mask


BATCHES = pd.Series(["Blank 1", "Blank 2", "Sample (A)", "sample b", "Calibration"])


def test_substring_match_is_case_insensitive_and_selects_multiple():
    mask = _name_mask(BATCHES, "blank", exact=False)

    assert BATCHES[mask].tolist() == ["Blank 1", "Blank 2"]


def test_substring_match_treats_regex_metacharacters_literally():
    # "(A)" is a regex group; as a literal substring it must match only the
    # batch that actually contains the parentheses, and must not raise.
    mask = _name_mask(BATCHES, "(A)", exact=False)

    assert BATCHES[mask].tolist() == ["Sample (A)"]


def test_exact_match_selects_only_the_full_name_case_insensitively():
    mask = _name_mask(BATCHES, "SAMPLE B", exact=True)

    assert BATCHES[mask].tolist() == ["sample b"]


def test_exact_match_does_not_match_a_substring():
    # "Blank" is a substring of "Blank 1"/"Blank 2" but not a full name.
    mask = _name_mask(BATCHES, "Blank", exact=True)

    assert BATCHES[mask].tolist() == []


def _params(func):
    return inspect.signature(func).parameters


def test_loaders_expose_exact_and_reject_unknown_kwargs():
    # `exact` is available, and the dead **kwargs that silently swallowed
    # typos like `batch=...` is gone, so unknown keywords now raise.
    for method in (MascopeClient.load_peaks, MascopeClient.load_peak_timeseries):
        params = _params(method)
        assert "exact" in params, f"{method.__name__} should expose 'exact'"
        assert not any(
            p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()
        ), f"{method.__name__} should not accept **kwargs"
