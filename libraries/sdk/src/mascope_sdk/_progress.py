"""Shared progress bar configuration."""

import sys

from tqdm import tqdm

#: Default tqdm keyword arguments used across the SDK.
_TQDM_DEFAULTS = {
    "file": sys.stderr,
    "bar_format": "{l_bar}{bar:30}{r_bar}",
    "colour": "green",
}


def progress_bar(total: int, desc: str, unit: str = "it") -> tqdm:
    """Create a tqdm progress bar with the SDK's default styling."""
    return tqdm(total=total, desc=desc, unit=unit, **_TQDM_DEFAULTS)
