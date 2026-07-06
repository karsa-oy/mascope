"""
Drift guard for the bundled package data.

`mascope init` materializes config/compose files from `mascope_cli/data/`,
which mirror the canonical copies at the repo root (used directly by the
monorepo workflows). The two sets must stay identical; when this test fails,
re-copy the repo-root file into `tooling/cli/src/mascope_cli/data/`.
"""

from pathlib import Path

import pytest

import mascope_cli
from mascope_cli.cmd.init import CONFIG_FILES


REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(mascope_cli.__file__).resolve().parent / "data"


@pytest.mark.parametrize("name", CONFIG_FILES)
def test_bundled_file_matches_repo_root(name):
    bundled = (DATA_DIR / name).read_bytes()
    canonical = (REPO_ROOT / name).read_bytes()

    assert bundled == canonical, (
        f"{name} drifted from the repo root — update the bundled copy: "
        f"cp {REPO_ROOT / name} {DATA_DIR / name}"
    )
