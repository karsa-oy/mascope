# pylint: disable=logging-fstring-interpolation,logging-format-interpolation,broad-exception-caught
#!/usr/bin/env python3
"""
Mascope CSV Export Agent

This application exports sample data from a Mascope server to CSV files,
performing compound matching and saving results for further analysis.
"""

import argparse
import json
import logging
import os
import time
import traceback
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

import pandas as pd

import mascope_sdk


mascope_sdk.SERVICE_NAME = "export-agent"
from mascope_sdk import get_sample_batches, get_sample_compounds_matches, get_samples


DEFAULT_CONFIG = {
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

    def load_config(self) -> dict:
        """Load configuration from file or create default."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                # Create default config file
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_CONFIG, f, indent=2)
                print(f"Created default configuration file: {self.config_file}")
                print(
                    "Please edit the configuration file with your Mascope server details."
                )
                return DEFAULT_CONFIG
        except Exception as e:
            print(f"Error loading config: {e}")
            return DEFAULT_CONFIG

    def load_state(self) -> dict:
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
            self.logger.debug("Saving state to file")
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

    def get_modified_batches(self) -> list[dict]:
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
                batch_id = batch["sample_batch_id"]
                batch_modified = batch["sample_batch_utc_modified"]

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

    def get_new_samples(self, batch_id: str) -> list[dict]:
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
                sample_id = sample["sample_item_id"]
                created_at = sample["sample_item_utc_created"]

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

    def process_sample(self, sample: dict) -> tuple[dict, dict]:
        """Process a single sample with compound matching.

        :param sample: The sample to process.
        :return: A tuple containing the processed sample and the matching results.
            Results is a dictionary with keys "formula" and values "intensity".
        """
        sample_id = sample["sample_item_id"]
        sample_name = sample["sample_item_name"]

        self.logger.info(f"Processing sample: {sample_name} (ID: {sample_id})")

        results = {}

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
            )
            if match_data is None:
                raise RuntimeError(f"Failed to get matches for sample {sample_id}")

            if len(match_data) > 0:
                for compound in match_data:
                    match_ions = compound.get("children", [])
                    for match_ion in match_ions:
                        intensity = (
                            match_ion["sample_peak_intensity_sum"]
                            if match_ion["match_score"]
                            >= self.config["match_params"]["match_score_threshold"]
                            else 0.0
                        )
                        results.update({match_ion["target_ion_formula"]: intensity})
                self.logger.info(
                    f"Found matches for {len(results)} ions in sample {sample_name}"
                )
            else:
                self.logger.info(f"No matches found in sample {sample_name}")

        except Exception as e:
            self.logger.error(
                f"Error in matching sample {sample_id}: {e}\n{traceback.format_exc()}"
            )

        self.logger.info(f"Finished matching for sample {sample_name}")
        return sample, results

    def save_results(self, results: list[tuple[dict, dict]]) -> bool:
        """Save match results to a single CSV file per day with columns for each compound."""
        self.logger.debug(f"Saving results for {len(results)} samples")
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.config["output_directory"], exist_ok=True)

            # Get today's date for the filename
            today = datetime.now().strftime("%Y%m%d")
            filename = f"{today}.csv"
            filepath = os.path.join(self.config["output_directory"], filename)

            # Load or create DataFrame
            if os.path.isfile(filepath):
                df = pd.read_csv(filepath)
            else:
                df = pd.DataFrame()

            new_rows = []
            for sample, result_row in results:
                # Prepare row data
                sample_datetime_utc = sample["datetime_utc"]
                sample_filename = sample["filename"]
                row_data = {
                    "datetime_utc": sample_datetime_utc,
                    "filename": sample_filename,
                }
                for formula, intensity in result_row.items():
                    if formula:
                        row_data[formula] = intensity

                # Add missing columns if needed
                for formula in row_data.keys():
                    if formula not in df.columns and formula not in [
                        "datetime_utc",
                        "filename",
                    ]:
                        df[formula] = ""
                new_rows.append(row_data)
            # Concatenate new data into existing dataframe
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            # Sort columns
            df = df[
                ["datetime_utc", "filename"]
                + [col for col in df.columns if col not in ["datetime_utc", "filename"]]
            ]
            # Save back to CSV
            df.to_csv(filepath, index=False)

            self.logger.info(f"Results saved to: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving results: {e}\n{traceback.format_exc()}")
            return False

    def update_state(self, last_check_timestamp: str, checked_batch_ids: list[str]):
        """Update the state with checked batches."""

        # Update last check timestamp
        self.state["last_check_timestamp"] = last_check_timestamp

        # Update batch check times
        for batch_id in checked_batch_ids:
            self.update_batch_state(last_check_timestamp, batch_id, save=False)

        self.save_state()

    def update_batch_state(
        self, last_check_timestamp: str, batch_id: str, save: bool = True
    ) -> None:
        """Update the state for a specific batch."""

        if "last_batch_check_times" not in self.state:
            self.state["last_batch_check_times"] = {}

        self.state["last_batch_check_times"][batch_id] = last_check_timestamp

        if save:
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
            batch_id = batch["sample_batch_id"]
            batch_name = batch["sample_batch_name"]

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
                # Update batch last check time
                self.update_batch_state(check_time, batch_id, save=True)
                continue

            # Process each new sample in this batch
            batch_successful_count = 0
            batch_results = []
            for i, sample in enumerate(new_samples):
                self.logger.info(
                    f"Processing sample {i + 1}/{len(new_samples)} in batch {batch_name}"
                )
                sample, sample_results = self.process_sample(sample)
                batch_results.append((sample, sample_results))
                batch_successful_count += 1
            # Save results
            saved = self.save_results(batch_results)
            if saved:
                self.update_batch_state(check_time, batch_id, save=True)
                total_successful_count += batch_successful_count
                checked_batch_ids.append(batch_id)
                self.logger.info(
                    f"Batch {batch_name}: processed {batch_successful_count}/{len(new_samples)} samples"
                )
            else:
                self.logger.error(f"Failed to save results for batch {batch_name}")

            if batch_successful_count < len(new_samples):
                self.logger.warning(
                    f"Some samples in batch {batch_name} failed to process"
                )

        # Update global state
        if checked_batch_ids:
            self.update_state(check_time, [])
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
