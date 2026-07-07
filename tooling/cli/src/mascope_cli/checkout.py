"""
Monorepo source-checkout detection.

The CLI has two audiences: developers running it editable from the monorepo,
and operators running it from a wheel. Developer commands (`dev`, `test`,
`agent`, `backend`) drive the source tree itself and are only registered when
the CLI actually runs from a checkout.
"""

from pathlib import Path


def source_checkout(anchor: Path | None = None) -> Path | None:
    """
    Repo root of the Mascope checkout the CLI runs from, if any.

    An editable install resolves ``mascope_cli`` inside the checkout
    (``<root>/tooling/cli/src/mascope_cli``); a wheel install resolves it in
    site-packages, where walking up never lands in the monorepo.

    :param anchor: Location of the mascope_cli package; defaults to the
                   imported package. Overridable for testing.
    :type anchor: Path, optional
    :return: The checkout root, or None when not running from source.
    :rtype: Path | None
    """
    if anchor is None:
        import mascope_cli

        anchor = Path(mascope_cli.__file__).resolve().parent
    # <root>/tooling/cli/src/mascope_cli -> root is 4 levels up.
    parents = anchor.parents
    if len(parents) < 4:
        return None
    root = parents[3]
    if (root / "pyproject.toml").is_file() and (root / "tooling" / "cli").is_dir():
        return root
    return None
