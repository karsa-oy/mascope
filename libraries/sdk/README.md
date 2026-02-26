# Mascope SDK

Python SDK for the Mascope mass spectrometry data analysis platform. Designed for researchers who want to load and analyze data from a Mascope server in Jupyter notebooks.

## Installation

```bash
pip install mascope_sdk
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add mascope_sdk
```

## Quick Start

### 1. Configure credentials

Create a `.env` file in your working directory (or any parent directory):

```env
MASCOPE_URL=https://example.mascope.app
MASCOPE_ACCESS_TOKEN=your-api-token
```

> **Tip:** Generate the API token in your Mascope instance's user settings.

### 2. Use the SDK

```python
from mascope_sdk import MascopeClient

# MascopeClient auto-loads user credentials from .env
mascope = MascopeClient()

# List workspaces
workspaces = mascope.workspaces.list()
print(f"Found {len(workspaces)} workspaces")

# List sample batches in a workspace
batches = mascope.batches.list(workspace_id=workspaces[0]["id"])

# Get samples from a batch
samples = mascope.samples.list(batch_id=batches[0]["id"])

# Get spectrum data from a sample
spectrum = mascope.samples.get_spectrum(sample_id=samples[0]["id"])

# Plot the spectrum
import matplotlib.pyplot as plt
plt.stem(spectrum["mz"], spectrum["intensity"])
plt.xlabel("m/z")
plt.ylabel(f"Intensity ({spectrum['intensity_unit']})")
plt.show()
```

## Configuration

The `MascopeClient` can be configured in three ways (in priority order):

1. **Constructor parameters** (highest priority):

   ```python
   mascope = MascopeClient(
       url="https://example.mascope.com",
       access_token="your-token"
   )
   ```

2. **Environment variables**:

   ```bash
   export MASCOPE_URL=https://mascope.example.com
   export MASCOPE_ACCESS_TOKEN=your-token
   ```

3. **`.env` file** (recommended for notebooks):
   ```env
   MASCOPE_URL=https://example.mascope.com
   MASCOPE_ACCESS_TOKEN=your-token
   ```

## API Reference

### MascopeClient

The main entry point for all API operations.

```python
from mascope_sdk import MascopeClient

mascope = MascopeClient()
```

### Resources

#### `mascope.workspaces`

- `list()` - List all accessible workspaces

#### `mascope.batches`

- `list(workspace_id)` - List sample batches in a workspace
- `get_data(batch_id)` - Get detailed batch data including samples and matches

#### `mascope.samples`

- `list(batch_id)` - List samples in a batch
- `get(sample_id)` - Get sample details
- `get_peaks(sample_id, ...)` - Get peak data with optional filtering
- `get_peak_timeseries(sample_id, mz, ...)` - Get intensity over time for a peak
- `get_spectrum(sample_id, ...)` - Get averaged spectrum
- `get_spectra(sample_ids, ...)` - Get spectra for multiple samples
- `get_centroids(sample_ids)` - Get centroid data

#### `mascope.matching`

- `match_compound(sample_id, formula, ...)` - Match a compound in a sample
- `match_compounds(sample_id, formulas, ...)` - Match multiple compounds

#### `mascope.ionization`

- `list()` - List available ionization mechanisms

#### `mascope.cheminfo`

- `query_by_mz(mz, mechanism_ids, ...)` - Query potential formulas for an m/z value

## Error Handling

The SDK raises specific exceptions for different error conditions:

```python
from mascope_sdk import MascopeClient
from mascope_sdk.exceptions import (
    AuthenticationError,
    NotFoundError,
    ConfigurationError,
)

try:
    mascope = MascopeClient()
    sample = mascope.samples.get("invalid-id")
except ConfigurationError:
    print("Missing MASCOPE_URL or MASCOPE_ACCESS_TOKEN")
except AuthenticationError:
    print("Invalid API token")
except NotFoundError:
    print("Sample not found")
```

### Exception Hierarchy

- `MascopeError` - Base exception
  - `ConfigurationError` - Missing/invalid configuration
  - `ConnectionError` - Network/connection issues
    - `TimeoutError` - Request timeout
  - `MascopeAPIError` - API errors
    - `AuthenticationError` - 401/403 responses
    - `NotFoundError` - 404 responses
    - `ValidationError` - 422 responses
    - `ServerError` - 5xx responses

## Common Examples

### Get peak timeseries and plot

```python
import matplotlib.pyplot as plt
from mascope_sdk import MascopeClient

mascope = MascopeClient()

# Get timeseries for a specific m/z
timeseries = mascope.samples.get_peak_timeseries(
    sample_id="sample-123",
    mz=180.063,
    mz_tolerance_ppm=5.0,
)

if timeseries:
    plt.plot(timeseries["time"], timeseries["height"])
    plt.xlabel("Time (s)")
    plt.ylabel("Intensity")
    plt.title(f"Peak at m/z {timeseries['mz']:.3f}")
    plt.show()
```

### Match compounds in a sample

```python
from mascope_sdk import MascopeClient

mascope = MascopeClient()

# Match multiple compounds
matches = mascope.matching.match_compounds(
    sample_id="sample-123",
    formulas=["C6H12O6", "C12H22O11", "C3H6O3"],
)

if matches:
    for compound in matches.get("compounds", []):
        print(f"Found: {compound['formula']}")
```

### Query chemical formulas by m/z

```python
from mascope_sdk import MascopeClient

mascope = MascopeClient()

# Get ionization mechanisms
mechanisms = mascope.ionization.list()
mech_ids = [m["id"] for m in mechanisms]

# Query potential formulas
results = mascope.cheminfo.query_by_mz(
    mz=180.063,
    ionization_mechanism_ids=mech_ids,
    mz_tolerance=30.0,
    limit=10,
)

for result in results:
    print(f"{result['formula']}: {result['mass']:.4f}")
```

## Migration from Legacy API

If you're using the old function-based API, you'll see deprecation warnings. Here's how to migrate:

| Old API                                                       | New API                                               |
| ------------------------------------------------------------- | ----------------------------------------------------- |
| `get_workspaces(url, token)`                                  | `mascope.workspaces.list()`                           |
| `get_sample_batches(url, token, ws_id)`                       | `mascope.batches.list(workspace_id)`                  |
| `get_samples(url, token, batch_id)`                           | `mascope.samples.list(batch_id)`                      |
| `get_sample(url, token, sample_id)`                           | `mascope.samples.get(sample_id)`                      |
| `get_sample_peaks(url, token, sample_id)`                     | `mascope.samples.get_peaks(sample_id)`                |
| `get_sample_spectrum(url, token, sample_id)`                  | `mascope.samples.get_spectrum(sample_id)`             |
| `get_sample_peak_timeseries(url, token, sample_id, mz)`       | `mascope.samples.get_peak_timeseries(sample_id, mz)`  |
| `get_sample_compound_matches(url, token, sample_id, formula)` | `mascope.matching.match_compound(sample_id, formula)` |
| `get_ionization_mechanisms(url, token)`                       | `mascope.ionization.list()`                           |
| `get_cheminfo_by_mz(url, token, mz, mech_ids)`                | `mascope.cheminfo.query_by_mz(mz, mech_ids)`          |

The legacy functions still work but will be removed in a future release.
