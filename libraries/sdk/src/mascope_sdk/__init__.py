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
    SERVICE_NAME,
    api_get,
    api_post,
    api_post_file,
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

__all__ = [
    # New API (recommended)
    "MascopeClient",
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
