"""
Tests for source-checkout detection (`mascope_cli.checkout`).

The detector decides whether developer commands (dev, test, agent, backend)
are registered at all: an editable install inside the monorepo gets them, a
wheel install in site-packages does not.
"""

from pathlib import Path

from mascope_cli.checkout import source_checkout


def _fake_checkout(tmp_path: Path) -> Path:
    """A directory tree shaped like the monorepo with an editable install."""
    root = tmp_path / "repo"
    (root / "tooling" / "cli" / "src" / "mascope_cli").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    return root


def test_detects_editable_install_in_checkout(tmp_path):
    root = _fake_checkout(tmp_path)
    anchor = root / "tooling" / "cli" / "src" / "mascope_cli"

    assert source_checkout(anchor) == root


def test_rejects_site_packages_install(tmp_path):
    # A wheel install: .../site-packages/mascope_cli with no repo above it.
    anchor = tmp_path / "venv" / "Lib" / "site-packages" / "mascope_cli"
    anchor.mkdir(parents=True)

    assert source_checkout(anchor) is None


def test_rejects_shallow_paths():
    # Fewer than four parents must not raise.
    assert source_checkout(Path("/")) is None


def test_this_test_run_is_a_checkout():
    # The suite itself runs from the monorepo, so the default anchor
    # (the imported package) must resolve to a repo root.
    root = source_checkout()
    assert root is not None
    assert (root / "tooling" / "cli").is_dir()


def test_dev_commands_registered_in_checkout(cli_runner):
    # In a checkout, the developer surface must be present alongside the
    # operator surface (the wheel-install branch is exercised in the Phase 4
    # packaging smoke test, where a real wheel is installed into a venv).
    from mascope_cli.main import app

    result = cli_runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("dev", "test", "agent", "backend"):
        assert command in result.output
