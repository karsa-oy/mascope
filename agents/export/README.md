# Mascope CSV Export Agent

A Python application that continuously monitors a Mascope server for new sample data in a specified workspace, processes samples with compound matching, and saves results to text files.

## Features

- **Continuous Monitoring**: Automatically checks for new samples at configurable intervals
- **Batch Tracking**: Tracks sample batches and detects modifications to avoid missing samples
- **Configurable Compound Matching**: Searches for specified target compounds in new samples
- **State Management**: Uses timestamp-based filtering to avoid processing duplicate samples
- **Result Export**: Saves compound match results to structured text files

## Usage

### 1. First Run

On first run, the application will create a default configuration file and exit. Edit this file with your Mascope server details and custom target list before running again.

### 2. Configuration

The application uses a JSON configuration file (`data_monitor_config.json`) to specify the configuration. The configurable parameters are explained in the following sections.

> **NOTE:** Any changes made to the configuration only take effect after restarting the application

#### Required Settings

- `mascope_url`: URL of your Mascope server (e.g., `"https://<org>.mascope.app"`)
- `access_token`: Your Mascope API access token (of type _Jupyter Notebooks_)

  > To generate the access token, log in to Mascope and via the _🏠Home menu_ enter _⚙️Settings_. In the _API access token_ section generate _Jupyter Notebooks_ token (or use an existing one).

- `workspace_id`: The workspace ID to monitor for samples

  > To retrieve the `workspace_id` of the Workspace you wish to monitor, the easiest way is to use a web browser and (while logged in) navigate to `https://<org>.mascope.app/api/workspaces`. Find the correct workspace and copy-paste the `workspace_id` into the configuration file.

- `target_compounds`: Array of molecular formulas to search for (e.g., `["H2SO4", "CH2O2", "C3H6O3"]`)
  > Note, these are the parent molecule formulae of interest. The ion compositions will be derived from these based on the ionization mechanisms configured for the batches from which the samples will be processed.

#### Optional Settings

- `match_params: {` Matching algorithm parameters:

  - `mz_tolerance`: Mass-to-charge ratio tolerance (ppm) for matching (default: 10.0)
  - `isotope_ratio_tolerance`: Isotope ratio tolerance (default: 0.2)
  - `peak_min_intensity`: Minimum peak intensity threshold (default: 0.0)

  `}`

- `output_directory`: Directory to save result files (default: `"./results"`)
- `check_interval_seconds`: How often to check for new samples (default: 10)
- `log_level`: Logging level (`"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`)
- `log_file`: Log file path (default: `"data_monitor.log"`)
- `state_file`: State file path (default: `"data_monitor_state.json"`)

#### Example Configuration

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

### 3. Continuous Monitoring

After configuring, to run the monitor continuously (checks for new samples every configured interval), simply run the executable `Mascope-CSV-Export-Agent.exe`.

> **NOTE**: When running the agent for the first time (after initial configuration), it will process all samples from all batches of the configured workspace.

> Consequently, in case you wish to edit the target list and recompute data retrospectively, you may stop the agent, delete `data_monitor_state.json`, and relaunch to trigger re-processing.

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

1. **Batch Detection**: Queries the Mascope server for all sample batches in the specified workspace
2. **Change Detection**: Compares batch modification timestamps with last check times
3. **Sample Filtering**: For modified batches, finds samples created since last check
4. **Compound Matching**: Searches each new sample for target compounds using the Mascope SDK
5. **Result Storage**: Saves match results to timestamped text files
6. **State Update**: Updates tracking information for next check cycle

The application is designed to never miss samples, even if they are added to previously processed batches or if new batches are created during processing.

## Extras

### Single Check mode

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
