# Mascope CSV Export Agent

A Python application that continuously monitors a Mascope server for new sample data in a specified workspace, processes samples with compound matching, and saves results to text files.

## Features

- **Continuous Monitoring**: Automatically checks for new samples at configurable intervals
- **Batch Tracking**: Tracks sample batches and detects modifications to avoid missing samples
- **Configurable Compound Matching**: Searches for specified target compounds in new samples
- **State Management**: Uses timestamp-based filtering to avoid processing duplicate samples
- **Result Export**: Saves compound match results to structured text files

## Configuration

The application uses a JSON configuration file (`data_monitor_config.json`) to specify:

### Required Settings

- `mascope_url`: URL of your Mascope server (e.g., `"https://org.mascope.app"`)
- `access_token`: Your Mascope API access token
- `workspace_id`: The workspace ID to monitor for samples

### Target Compounds

- `target_compounds`: Array of molecular formulas to search for (e.g., `["H2SO4", "CH2O2", "C3H6O3"]`)

### Match Parameters

- `mz_tolerance`: Mass-to-charge ratio tolerance for matching (default: 10.0)
- `isotope_ratio_tolerance`: Isotope ratio tolerance (default: 0.2)
- `peak_min_intensity`: Minimum peak intensity threshold (default: 0.0)

### Optional Settings

- `output_directory`: Directory to save result files (default: `"./results"`)
- `check_interval_seconds`: How often to check for new samples (default: 10)
- `log_level`: Logging level (`"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`)
- `log_file`: Log file path (default: `"data_monitor.log"`)
- `state_file`: State file path (default: `"data_monitor_state.json"`)

### Example Configuration

```json
{
  "mascope_url": "https://org.mascope.app",
  "access_token": "your-access-token-here",
  "workspace_id": "your-workspace-id",
  "target_compounds": ["H2SO4", "CH2O2", "C3H6O3", "NH3"],
  "match_params": {
    "mz_tolerance": 10.0,
    "isotope_ratio_tolerance": 0.2,
    "peak_min_intensity": 0.0
  },
  "output_directory": "./results",
  "check_interval_seconds": 10,
  "log_level": "INFO"
}
```

## Usage

### First Run

On first run, the application will create a default configuration file. Edit this file with your Mascope server details and custom target list before running again.

### Continuous Monitoring

To run the monitor continuously (checks for new samples every configured interval), simply run the executable `Mascope-CSV-Export-Agent.exe`.

Alternatively, to run directly from the source code:

```bash
> python src/main.py
```

### Single Check

Run a single check cycle and exit:

```bash
> Mascope-CSV-Export-Agent.exe --single
```

Or from source:

```bash
> python src/main.py --single
```

### Custom Configuration File

Use a different configuration file:

```bash
> python src/main.py --config my_config.json
```

## Output

### Result Files

- Results are saved as timestamped text files in the configured output directory
- Each file contains compound match data in JSON format
- Files are named with format: `YYYYMMDD_HHMMSS_orbion.txt`

### Log Files

- Application logs are written to the configured log file and console
- Includes information about batches processed, samples found, and any errors

### State Management

- The application maintains state in `data_monitor_state.json`
- Tracks last check timestamps per batch to avoid reprocessing samples
- State file is automatically created and updated

## How It Works

1. **Batch Detection**: Queries the Mascope server for all sample batches
2. **Change Detection**: Compares batch modification timestamps with last check times
3. **Sample Filtering**: For modified batches, finds samples created since last check
4. **Compound Matching**: Searches each new sample for target compounds using the Mascope SDK
5. **Result Storage**: Saves match results to timestamped text files
6. **State Update**: Updates tracking information for next check cycle

The application is designed to never miss samples, even if they are added to previously processed batches or if new batches are created during processing.
