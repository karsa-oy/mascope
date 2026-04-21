"""
Fixtures for backend unit tests that exercise Mascope Tools against ChemInfo.

Provides a session-scoped reachability check for the public ChemInfo HTTP
endpoint so that every test in this package is automatically skipped  when
the endpoint is unavailable.
"""

import warnings

import httpx
import pytest

from mascope_backend.api.new.cheminfo.config import cheminfo_config


@pytest.fixture(scope="session")
def cheminfo_reachable() -> bool:
    """Check once per session whether the ChemInfo endpoint is reachable.

    Issues a warning and returns False when the endpoint
    cannot be reached within a short timeout so that dependent tests can be
    skipped gracefully.

    :return: True if the ChemInfo endpoint responded, False otherwise.
    :rtype: bool
    """
    try:
        with httpx.Client(timeout=3.0) as client:
            client.get(cheminfo_config.BASE_URL)
        return True
    except Exception:
        warnings.warn(
            f"ChemInfo endpoint at {cheminfo_config.BASE_URL!r} is unavailable. "
            "All composition-vs-ChemInfo tests will be skipped.",
            stacklevel=1,
        )
        return False


@pytest.fixture(autouse=True)
def skip_if_cheminfo_unavailable(cheminfo_reachable: bool) -> None:
    """Skip the current test when the ChemInfo endpoint is unavailable.

    Function-scoped and autouse=True so every parametrized case is
    individually reported as skipped rather than failing at collection time.

    :param cheminfo_reachable: Session-scoped flag from cheminfo_reachable.
    :type cheminfo_reachable: bool
    """
    if not cheminfo_reachable:
        warnings.warn(
            "Skipping test because ChemInfo endpoint is unavailable.", stacklevel=2
        )
        pytest.skip()
