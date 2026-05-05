"Configuration constants for MS2 analysis."

# Tolerance for matching fragment peaks by m/z (Da)
MZ_MATCH_TOLERANCE = 0.01
# Minimum fraction of MS2 TIC for a fragment to be considered present
MIN_TIC_FRACTION = 0.01
# Default signal-to-noise ratio threshold for filtering out noise peaks in the spectra.
DEFAULT_NOISE_THRESHOLD = 10
# Default tolerance for merging near-duplicate parent peaks (in Da).
DEFAULT_PARENT_PEAK_TOLERANCE = 0.001
# Max number of fragment traces to show in timeseries (to avoid overcrowding)
MAX_FRAGMENT_TRACES = 20
# Default number of top fragments to show in the table for each parent peak
DEFAULT_MAX_FRAGMENTS = 10
