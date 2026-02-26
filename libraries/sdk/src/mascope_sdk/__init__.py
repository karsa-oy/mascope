import warnings

from requests.packages.urllib3.exceptions import InsecureRequestWarning

from ._legacy import (
    # Internal helpers (used by agents)
    SERVICE_NAME,
    api_get,
    api_post,
    api_post_file,
    # Deprecated public functions
    get_workspaces,
    get_sample_batches,
    get_sample_batch_data,
    get_samples,
    get_sample,
    get_sample_compound_matches,
    get_sample_compounds_matches,
    get_sample_peaks,
    get_sample_peak_timeseries,
    get_sample_spectrum,
    get_samples_spectra,
    get_sample_centroids_per_scan,
    get_sample_file_peaks,
    get_sample_file_peak_timeseries,
    get_sample_file_spectrum,
    get_sample_file_instrument_config,
    get_sample_file_metadata,
    get_ionization_mechanisms,
    get_cheminfo_by_mz,
)

# Suppress only the InsecureRequestWarning from requests
warnings.simplefilter("ignore", InsecureRequestWarning)

__all__ = [
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
