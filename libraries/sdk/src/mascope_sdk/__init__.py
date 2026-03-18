"""Mascope SDK - Python client for the Mascope API.

This library provides a Pythonic interface to the Mascope mass spectrometry
data analysis platform. It is designed for researchers working in Jupyter
notebooks who want to load and analyze data from a Mascope server.

For detailed documentation, see the README and docstrings.
"""

from importlib.metadata import version

# Version of the SDK (read from pyproject.toml via installed package metadata)
__version__ = version("mascope_sdk")

# Legacy API exports (deprecated, kept for backwards compatibility)
from ._legacy import (  # Internal helpers (used by agents); Deprecated public functions
    SERVICE_NAME,  # noqa: F401 pylint: disable=unused-import
    api_get,  # noqa: F401 pylint: disable=unused-import
    api_post,  # noqa: F401 pylint: disable=unused-import
    api_post_file,  # noqa: F401 pylint: disable=unused-import
    get_cheminfo_by_mz,
    get_ionization_mechanisms,
    get_sample,
    get_sample_batch_data,
    get_sample_batches,
    get_sample_centroids_per_scan,
    get_sample_compound_matches,
    get_sample_compounds_matches,
    get_sample_file_instrument_config,
    get_sample_file_metadata,
    get_sample_file_peak_timeseries,
    get_sample_file_peaks,
    get_sample_file_spectrum,
    get_sample_peak_timeseries,
    get_sample_peaks,
    get_sample_spectrum,
    get_samples,
    get_samples_spectra,
    get_workspaces,
)

# New API exports
from .client import MascopeClient

# pylint: disable=redefined-builtin
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    MascopeAPIError,
    MascopeConnectionError,
    MascopeError,
    MascopeTimeoutError,
    NotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
)


def copy_examples(dest: str = "./mascope_examples") -> None:
    """Copy the bundled example notebooks to a local directory.

    :param dest: Target directory. Created if it doesn't exist.
                 Existing files are **not** overwritten.
    """
    from importlib.resources import files  # pylint: disable=import-outside-toplevel
    from pathlib import Path  # pylint: disable=import-outside-toplevel

    src = files("mascope_sdk").joinpath("examples")
    dest_path = Path(dest)
    dest_path.mkdir(parents=True, exist_ok=True)

    copied = 0
    for item in src.iterdir():
        if item.name.endswith(".ipynb"):
            target = dest_path / item.name
            if target.exists():
                print(f"  skip (exists): {target}")
                continue
            with open(target, "wb") as f:
                f.write(item.read_bytes())
            copied += 1
            print(f"  copied: {target}")

    print(f"\n{copied} notebook(s) copied to {dest_path.resolve()}")


__all__ = [
    # New API (recommended)
    "MascopeClient",
    "copy_examples",
    # Exceptions
    "MascopeError",
    "ConfigurationError",
    "MascopeAPIError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "ServerError",
    "ConnectionError",  # Alias for MascopeConnectionError
    "TimeoutError",  # Alias for MascopeTimeoutError
    "MascopeConnectionError",
    "MascopeTimeoutError",
    # Legacy functions (deprecated, kept for backwards compatibility)
    "get_workspaces",
    "get_sample_batches",
    "get_sample_batch_data",
    "get_samples",
    "get_sample",
    "get_sample_compound_matches",
    "get_sample_compounds_matches",
    "get_sample_peaks",
    "get_sample_peak_timeseries",
    "get_sample_spectrum",
    "get_samples_spectra",
    "get_sample_centroids_per_scan",
    "get_sample_file_peaks",
    "get_sample_file_peak_timeseries",
    "get_sample_file_spectrum",
    "get_sample_file_instrument_config",
    "get_sample_file_metadata",
    "get_ionization_mechanisms",
    "get_cheminfo_by_mz",
]
