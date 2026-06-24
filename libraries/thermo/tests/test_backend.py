"""Tests for the reader-backend selection seam (``mascope_thermo.backend``).

These cover the ``MASCOPE_THERMO_BACKEND`` switch and don't read any file, so
they run anywhere.
"""

import pytest

from mascope_thermo import backend as m_backend


def test_default_backend_is_opentfraw(monkeypatch):
    monkeypatch.delenv(m_backend.ENV_BACKEND, raising=False)
    be = m_backend.open_backend("dummy.raw")
    assert isinstance(be, m_backend.OpenTFRawBackend)
    # OpenTFRawBackend structurally satisfies the ReaderBackend protocol.
    assert isinstance(be, m_backend.ReaderBackend)


def test_explicit_thermo_backend(monkeypatch):
    monkeypatch.setenv(m_backend.ENV_BACKEND, "thermo")
    assert isinstance(m_backend.open_backend("dummy.raw"), m_backend.ThermoBackend)


def test_backend_name_is_case_insensitive(monkeypatch):
    monkeypatch.setenv(m_backend.ENV_BACKEND, "Thermo")
    assert isinstance(m_backend.open_backend("dummy.raw"), m_backend.ThermoBackend)


def test_opentfraw_backend_selected(monkeypatch):
    monkeypatch.setenv(m_backend.ENV_BACKEND, "opentfraw")
    be = m_backend.open_backend("dummy.raw")
    assert isinstance(be, m_backend.OpenTFRawBackend)
    assert isinstance(be, m_backend.ReaderBackend)


def test_unknown_backend_raises(monkeypatch):
    monkeypatch.setenv(m_backend.ENV_BACKEND, "bogus")
    with pytest.raises(ValueError):
        m_backend.open_backend("dummy.raw")
