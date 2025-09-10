# pylint: disable=logging-fstring-interpolation,logging-format-interpolation,broad-exception-caught
#!/usr/bin/env python3
"""
Mascope CSV Export Agent

This application exports sample data from a Mascope server to CSV files,
performing compound matching and saving results for further analysis.
"""

import argparse
import json
import os
import time
import logging
import traceback

from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Dict, List

import mascope_sdk

mascope_sdk.SERVICE_NAME = "export-agent"
from mascope_sdk import get_sample_batches, get_samples, get_sample_compounds_matches


class DataMonitor:
    """Monitors Mascope server for new sample data and processes it."""

    def __init__(self, config_file: str = "config.json"):
        """
        Initialize the data monitor.

        :param config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config = self.load_config()
        self.state_file = self.config.get("state_file", "state.json")
        self.state = self.load_state()

        # Setup logging
        self.setup_logging()

        # Validate configuration
        self.validate_config()

    def load_config(self) -> Dict:
        """Load configuration from file or create default."""
        default_config = {
            "mascope_url": "http://localhost:8090",
            "access_token": "",
            "workspace_id": "",
            "target_compounds": ["CH2O2", "C3H6O3"],
            "match_params": {
                "mz_tolerance": 15.0,
                "isotope_ratio_tolerance": 0.2,
                "peak_min_intensity": 0.0,
                "match_score_threshold": 0.5,
            },
            "output_directory": "./results",
            "check_interval_seconds": 10,
            "state_file": "state.json",
            "log_level": "INFO",
            "log_file": "export_agent.log",
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                # Create default config file
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=2)
                print(f"Created default configuration file: {self.config_file}")
                print(
                    "Please edit the configuration file with your Mascope server details."
                )
                return default_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return default_config

    def load_state(self) -> Dict:
        """Load state from file or create default."""
        default_state = {
            "last_check_timestamp": None,
            "last_batch_check_times": {},  # batch_id -> last_check_timestamp
        }

        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                # Ensure new field exists in loaded state
                if "last_batch_check_times" not in state:
                    state["last_batch_check_times"] = {}
                return state
            else:
                return default_state
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")
            return default_state

    def save_state(self):
        """Save current state to file."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")

    def setup_logging(self):
        """Setup logging configuration."""
        log_level = getattr(logging, self.config.get("log_level", "INFO").upper())
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                RotatingFileHandler(
                    self.config.get("log_file", "export_agent.log"),
                    maxBytes=10_000_000,  # 10MB
                    backupCount=5,
                ),
                logging.StreamHandler(),
            ],
        )

        self.logger = logging.getLogger(__name__)

    def validate_config(self):
        """Validate configuration and create output directory."""
        required_fields = ["mascope_url", "access_token", "workspace_id"]

        for field in required_fields:
            if not self.config.get(field):
                raise ValueError(f"Configuration missing required field: {field}")

        # Create output directory if it doesn't exist
        output_dir = self.config["output_directory"]
        os.makedirs(output_dir, exist_ok=True)

        self.logger.info(f"Output directory: {output_dir}")

    def get_modified_batches(self) -> List[Dict]:
        """Get all sample batches that have been modified since last check."""
        try:
            batches = get_sample_batches(
                mascope_url=self.config["mascope_url"],
                access_token=self.config["access_token"],
                workspace_id=self.config["workspace_id"],
            )

            if not batches:
                self.logger.info("No sample batches found")
                return []

            modified_batches = []
            last_batch_checks = self.state.get("last_batch_check_times", {})

            for batch in batches:
                batch_id = batch.get("sample_batch_id")
                batch_modified = batch.get("sample_batch_utc_modified", "")

                if not batch_id:
                    continue

                # If we haven't seen this batch before, include it
                if batch_id not in last_batch_checks:
                    modified_batches.append(batch)
                    continue

                # Check if batch was modified since our last check
                last_check = last_batch_checks[batch_id]
                if batch_modified and last_check:
                    try:
                        # Parse batch modification time
                        batch_time = datetime.fromisoformat(
                            batch_modified.replace("Z", "+00:00")
                        )
                        # Parse last check time
                        last_check_time = datetime.fromisoformat(last_check)

                        # Ensure both datetimes have timezone info for comparison
                        if batch_time.tzinfo is None:
                            batch_time = batch_time.replace(tzinfo=timezone.utc)
                        if last_check_time.tzinfo is None:
                            last_check_time = last_check_time.replace(
                                tzinfo=timezone.utc
                            )

                        if batch_time > last_check_time:
                            modified_batches.append(batch)
                    except Exception as e:
                        self.logger.warning(
                            f"Error parsing timestamp for batch {batch_id}: {e}"
                        )
                        # Include batch if we can't parse timestamps to be safe
                        modified_batches.append(batch)

            self.logger.info(f"Found {len(modified_batches)} modified batches")

            for batch in modified_batches:
                self.logger.info(
                    f"Modified batch: {batch.get('sample_batch_name', 'Unknown')} "
                    f"(ID: {batch.get('sample_batch_id', 'Unknown')})"
                )

            return modified_batches

        except Exception as e:
            self.logger.error(f"Error getting modified batches: {e}")
            return []

    def get_new_samples(self, batch_id: str) -> List[Dict]:
        """Get new samples from batch created since last check using timestamp comparison."""
        try:
            samples = get_samples(
                mascope_url=self.config["mascope_url"],
                access_token=self.config["access_token"],
                sample_batch_id=batch_id,
            )

            if not samples:
                self.logger.info("No samples found in batch")
                return []

            # Use the last check timestamp for this specific batch, or global last check
            batch_last_check = self.state.get("last_batch_check_times", {}).get(
                batch_id
            )
            global_last_check = self.state.get("last_check_timestamp")

            # Use batch-specific check time if available, otherwise use global
            last_check = batch_last_check or global_last_check

            new_samples = []
            for sample in samples:
                sample_id = sample.get("sample_item_id")
                created_at = sample.get("sample_item_utc_created", "") or sample.get(
                    "created_at", ""
                )

                # If we have a last check timestamp, filter by creation time
                if last_check and created_at:
                    try:
                        # Parse sample creation time
                        sample_time = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )

                        # Parse last check time
                        last_check_time = datetime.fromisoformat(last_check)

                        # Ensure both datetimes have timezone info for comparison
                        if sample_time.tzinfo is None:
                            sample_time = sample_time.replace(tzinfo=timezone.utc)
                        if last_check_time.tzinfo is None:
                            last_check_time = last_check_time.replace(
                                tzinfo=timezone.utc
                            )

                        if sample_time <= last_check_time:
                            continue
                    except Exception as e:
                        self.logger.warning(
                            f"Error parsing timestamp for sample {sample_id}: {e}"
                        )
                        # Include sample if we can't parse timestamps to be safe

                new_samples.append(sample)

            self.logger.info(
                f"Found {len(new_samples)} new samples in batch {batch_id}"
            )
            return new_samples

        except Exception as e:
            self.logger.error(f"Error getting new samples: {e}")
            return []

    def process_sample(self, sample: Dict) -> bool:
        """Process a single sample with compound matching."""
        sample_id = sample["sample_item_id"]
        sample_name = sample["sample_item_name"]

        self.logger.info(f"Processing sample: {sample_name} (ID: {sample_id})")

        results = []

        formulae = self.config["target_compounds"]
        try:
            self.logger.debug(
                f"Matching {len(formulae)} compounds in sample {sample_id}"
            )

            match_data = get_sample_compounds_matches(
                mascope_url=self.config["mascope_url"],
                access_token=self.config["access_token"],
                sample_item_id=sample_id,
                target_compound_formulas=formulae,
                match_params=self.config["match_params"],
                service_name="export-agent",
            )
            if len(match_data) > 0:
                for compound in match_data:
                    match_ions = compound.get("children", [])
                    results.extend(
                        [
                            {
                                "formula": match_ion["target_ion_formula"],
                                "intensity": match_ion["sample_peak_intensity_sum"],
                            }
                            for match_ion in match_ions
                            if match_ion["match_score"]
                            >= self.config["match_params"]["match_score_threshold"]
                        ]
                    )
                self.logger.info(
                    f"Found matches for {len(results)} ions in sample {sample_name}"
                )
            else:
                self.logger.info(f"No matches found in sample {sample_name}")

        except Exception as e:
            self.logger.error(
                f"Error in matching sample {sample_id}: {e}\n{traceback.format_exc()}"
            )

        # Save results to file
        if results:
            return self.save_results(sample, results)
        else:
            self.logger.info(f"No matches found for sample {sample_name}")
            return True

    def save_results(self, sample: Dict, results: List[Dict]) -> bool:
        """Save match results to a single CSV file per day with columns for each compound."""
        self.logger.debug(
            f"Saving results for sample {sample['sample_item_id']}: results={results}"
        )
        try:
            sample_datetime_utc = sample.get("datetime_utc")
            sample_filename = sample.get("filename", "")

            # Create output directory if it doesn't exist
            os.makedirs(self.config["output_directory"], exist_ok=True)

            # Get today's date for the filename
            today = datetime.now().strftime("%Y%m%d")
            filename = f"{today}.csv"
            filepath = os.path.join(self.config["output_directory"], filename)

            # Extract formulas and intensities from results
            formula_intensities = {}
            for result in results:
                formula = result.get("formula")
                intensity = result.get("intensity", "")
                if formula:
                    formula_intensities[formula] = intensity

            # Check if file already exists
            file_exists = os.path.isfile(filepath)
            existing_formulas = set()

            if file_exists:
                # Read existing headers to check if we need to update the file structure
                with open(filepath, "r", encoding="utf-8") as f:
                    header_line = f.readline().strip()
                    headers = header_line.split(",")
                    # Skip datetime and filename columns
                    existing_formulas = set(headers[2:])

            # Check if any new formulas exist in the results
            new_formulas = set(formula_intensities.keys()) - existing_formulas

            # If there are new formulas, we need to create a new file with updated headers
            if new_formulas and file_exists:
                self.logger.info(
                    f"Found new compounds: {new_formulas}. Creating updated CSV file."
                )

                # Read all existing data
                with open(filepath, "r", encoding="utf-8") as f:
                    existing_data = f.readlines()

                # Create a new file with updated headers
                temp_filepath = f"{filepath}.temp"
                with open(temp_filepath, "w", encoding="utf-8", newline="") as f:
                    # Combine existing headers with new formulas
                    all_formulas = sorted(list(existing_formulas.union(new_formulas)))
                    new_header = (
                        "datetime_utc,filename," + ",".join(all_formulas) + "\n"
                    )
                    f.write(new_header)

                    # Write existing data with placeholders for new columns
                    for i, line in enumerate(existing_data):
                        if i == 0:  # Skip header line
                            continue

                        parts = line.strip().split(",")
                        line_datetime = parts[0]
                        line_filename = parts[1]

                        # Create a dictionary mapping formula to value
                        # Adjust index to account for datetime and filename columns
                        line_values = {
                            headers[j]: parts[j] for j in range(2, len(parts))
                        }

                        # Create updated line with placeholders for new formulas
                        new_line = [line_datetime, line_filename]
                        for formula in all_formulas:
                            new_line.append(line_values.get(formula, ""))

                        f.write(",".join(new_line) + "\n")

                # Replace the old file with the updated one
                os.replace(temp_filepath, filepath)

                # Update existing_formulas for the next step
                existing_formulas = set(all_formulas)

            # Append data to the file
            with open(
                filepath, "a" if file_exists else "w", encoding="utf-8", newline=""
            ) as f:
                # Write header if creating a new file
                if not file_exists:
                    all_formulas = sorted(list(formula_intensities.keys()))
                    header = "datetime_utc,filename," + ",".join(all_formulas) + "\n"
                    f.write(header)
                    existing_formulas = set(all_formulas)

                # Prepare the data row
                data_row = [sample_datetime_utc, sample_filename]
                for formula in sorted(list(existing_formulas)):
                    data_row.append(str(formula_intensities.get(formula, "")))

                f.write(",".join(data_row) + "\n")

            self.logger.info(f"Results saved to: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving results: {e}\n{traceback.format_exc()}")
            return False

    def update_state(self, last_check_timestamp: str, checked_batch_ids: List[str]):
        """Update the state with checked batches."""

        # Update last check timestamp
        self.state["last_check_timestamp"] = last_check_timestamp

        # Update batch check times
        if "last_batch_check_times" not in self.state:
            self.state["last_batch_check_times"] = {}

        for batch_id in checked_batch_ids:
            self.state["last_batch_check_times"][batch_id] = last_check_timestamp

        # Clean up old batch check times (keep last 100 to prevent unlimited growth)
        batch_check_times = self.state["last_batch_check_times"]
        if len(batch_check_times) > 100:
            # Sort by timestamp and keep the most recent 100
            sorted_batches = sorted(
                batch_check_times.items(), key=lambda x: x[1], reverse=True
            )
            self.state["last_batch_check_times"] = dict(sorted_batches[:100])

        self.save_state()

    def run_single_check(self):
        """Run a single data check cycle."""
        self.logger.info("Starting data check cycle")

        # Get all modified batches
        check_time = datetime.now(timezone.utc).isoformat()
        modified_batches = self.get_modified_batches()
        if not modified_batches:
            self.logger.info("No modified batches to check")
            return

        # Process each modified batch
        checked_batch_ids = []
        total_successful_count = 0
        total_new_samples = 0

        for batch in modified_batches:
            batch_id = batch.get("sample_batch_id")
            batch_name = batch.get("sample_batch_name", "Unknown")

            if not batch_id:
                self.logger.error(f"Batch missing ID: {batch_name}")
                continue

            self.logger.info(f"Checking batch: {batch_name} (ID: {batch_id})")

            # Get new samples from this batch
            new_samples = self.get_new_samples(batch_id)
            total_new_samples += len(new_samples)

            if not new_samples:
                self.logger.info(f"No new samples in batch {batch_name}")
                checked_batch_ids.append(batch_id)
                continue

            # Process each new sample in this batch
            batch_successful_count = 0

            for sample in new_samples:
                sample_id = sample.get("sample_item_id")

                if self.process_sample(sample):
                    batch_successful_count += 1
                else:
                    self.logger.error(f"Failed to process sample {sample_id}")

            total_successful_count += batch_successful_count
            checked_batch_ids.append(batch_id)

            self.logger.info(
                f"Batch {batch_name}: processed {batch_successful_count}/{len(new_samples)} samples"
            )

        # Update state with checked batches
        if checked_batch_ids:
            self.update_state(check_time, checked_batch_ids)
            self.logger.info(
                f"Total: processed {total_successful_count}/{total_new_samples} samples "
                f"from {len(modified_batches)} batches"
            )

        self.logger.info("Data check cycle completed")

    def run_continuous(self):
        """Run continuous monitoring."""
        self.logger.info("Starting continuous data monitoring")
        self.logger.info(
            f"Check interval: {self.config['check_interval_seconds']} seconds"
        )

        try:
            while True:
                try:
                    self.run_single_check()
                except Exception as e:
                    self.logger.error(f"Error in check cycle: {e}")

                # Wait for next check
                time.sleep(self.config["check_interval_seconds"])

        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Fatal error in continuous monitoring: {e}")
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Mascope CSV Export Agent")
    parser.add_argument(
        "--config", default="config.json", help="Configuration file path"
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Run single check instead of continuous monitoring",
    )

    args = parser.parse_args()

    try:
        monitor = DataMonitor(config_file=args.config)

        if args.single:
            monitor.run_single_check()
        else:
            monitor.run_continuous()

    except Exception as e:
        print(f"Error: {e}")
        return


if __name__ == "__main__":
    main()
