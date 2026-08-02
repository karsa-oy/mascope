"""Tests: the demo-seed production safeguard.

``seed_demo`` creates a well-known owner+superuser (demo@mascope.app) with fixed
public API tokens. It must refuse to run unless ``MASCOPE_ALLOW_DEMO_SEED`` is
explicitly set, so it can never create a public-credential backdoor on a real
deployment. Regression cover for the pre-hardening state where the script would
seed against whatever database was active.
"""

import pytest

from mascope_backend.db.scripts.seed_demo import (
    DEMO_SEED_ENV_FLAG,
    _demo_seed_allowed,
    seed_demo,
)


@pytest.mark.asyncio
async def test_seed_demo_refuses_without_flag(monkeypatch):
    """Without the opt-in flag, seeding fails closed before touching the DB."""
    monkeypatch.delenv(DEMO_SEED_ENV_FLAG, raising=False)
    with pytest.raises(RuntimeError, match=DEMO_SEED_ENV_FLAG):
        await seed_demo()


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_flag_truthy_values_enable_seed(monkeypatch, value):
    monkeypatch.setenv(DEMO_SEED_ENV_FLAG, value)
    assert _demo_seed_allowed() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "nope"])
def test_flag_falsy_values_keep_seed_disabled(monkeypatch, value):
    monkeypatch.setenv(DEMO_SEED_ENV_FLAG, value)
    assert _demo_seed_allowed() is False


def test_flag_absent_keeps_seed_disabled(monkeypatch):
    monkeypatch.delenv(DEMO_SEED_ENV_FLAG, raising=False)
    assert _demo_seed_allowed() is False
