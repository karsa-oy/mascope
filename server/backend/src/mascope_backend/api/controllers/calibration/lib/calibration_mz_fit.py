"""
Functionalities related to the m/z fitting calibration processes.
"""

import numpy as np
import pandas as pd
from zarr.errors import PathNotFoundError

from mascope_tofwerk.calibration import mz_calibrate, tof_to_mass


import mascope_file.name as m_name
import mascope_file.io as m_io
import mascope_signal.compute as m_compute

from mascope_match import compute_match_isotopes
from mascope_match.params import TofMatchParams, OrbiMatchParams
from mascope_backend.api.lib.api_features import (
    api_controller,
)
from mascope_backend.api.new.instrument_configs.lib import (
    read_instrument_functions,
)
from mascope_backend.api.controllers.target.isotopes.target_isotopes_controller import (
    get_target_isotopes,
)
from mascope_backend.api.controllers.target.associations.target_compound_in_target_collection_controller import (
    get_target_compound_in_target_collection,
)
from mascope_backend.socket.notifications import (
    send_progress_user_notification,
)
from mascope_backend.api.models.calibration.calibration_pydantic_model import (
    CalibrationFitParams,
)

from mascope_backend.runtime import runtime


class BaseCalibrationHandler:
    def __init__(
        self,
        filename: str,
        params: CalibrationFitParams,
        notification: object = None,
    ):
        self.filename = filename
        self.params = params
        self.notification = notification
        self.fit_result = None
        self.stats = None
        self.error = None
        self.warning = None

    async def _match_calibration_compounds(
        self, match_params
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Match calibration compounds in the sample file."""
        target_compounds_result = await get_target_compound_in_target_collection(
            target_collection_id=self.params.calibration_collection_id,
        )
        target_compound_ids = [
            item["target_compound_id"] for item in target_compounds_result["data"]
        ]

        target_isotopes_result = await get_target_isotopes(
            target_compound_ids=target_compound_ids,
            ionization_mechanism_ids=self.params.ionization_mechanism_ids,
        )
        target_isotopes_df = pd.DataFrame(target_isotopes_result["data"])

        instrument_functions = await read_instrument_functions(self.filename)

        match_isotope_df = await compute_match_isotopes(
            filename=self.filename,
            target_isotopes_df=target_isotopes_df,
            match_params=match_params,
            instrument_functions=instrument_functions,
        )

        good_matches_df = match_isotope_df[
            (match_isotope_df.relative_abundance >= self.params.isotope_abundance_min)
            & (match_isotope_df.sample_peak_intensity >= self.params.peak_intensity_min)
            & (abs(match_isotope_df.match_mz_error) <= self.params.refine_window)
            & (match_isotope_df.match_score >= self.params.match_score_min)
            & (match_isotope_df.sample_peak_id != -1)
        ]

        return match_isotope_df, good_matches_df

    def _get_summary_row(self, calibration_df):
        return {
            "match_mz_error": abs(calibration_df["match_mz_error"]).mean(),
            "calibration_mz_error": abs(calibration_df["calibration_mz_error"]).mean(),
            "mz_error_diff": sum(calibration_df["mz_error_diff"]),
            "calibrant_to_tic": sum(calibration_df["calibrant_to_tic"]),
        }

    async def fit(self):
        """
        Fit method to be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    async def apply(self, fit: dict):
        """
        Apply method to be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def to_dict(self):
        return {
            "fit": self.fit_result,
            "stats": self.stats,
            "error": self.error,
            "warning": self.warning,
        }


class TofCalibrationHandler(BaseCalibrationHandler):

    @api_controller()
    async def fit(self):
        """Fit the m/z calibration for a TOF instrument."""
        match_params = TofMatchParams(
            mz_tolerance=self.params.mz_error_tolerance,
            peak_min_intensity=self.params.peak_intensity_min,
        )
        match_params.min_isotope_abundance = self.params.isotope_abundance_min

        await send_progress_user_notification(self.notification, 0.25)

        _, tic_per_scan = m_compute.get_tic_per_scan(self.filename)
        tic = np.sum(tic_per_scan)
        if tic < self.params.tic_threshold:
            self.warning = "TIC is too low! Check ionization device."
            return self.fit_result, self.stats, self.error, self.warning

        await send_progress_user_notification(self.notification, 0.35)

        match_isotope_df, good_matches_df = await self._match_calibration_compounds(
            match_params
        )

        n_relevant_isotopes = len(
            match_isotope_df[
                (
                    match_isotope_df.relative_abundance
                    >= self.params.isotope_abundance_min
                )
            ]
        )
        calibrant_signal_intensity = good_matches_df["sample_peak_intensity"]
        calibrant_to_tic = calibrant_signal_intensity / tic

        await send_progress_user_notification(self.notification, 0.75)

        if (
            n_relevant_isotopes >= 3
            and len(good_matches_df) >= 3
            and (n_relevant_isotopes - len(good_matches_df) <= 2)
        ):
            self.fit_result, self.stats = mz_calibrate(
                good_matches_df["sample_peak_tof"],
                good_matches_df["sample_peak_mz"],
                good_matches_df["mz"],
            )
            calibration_df = good_matches_df.copy().assign(
                calibration_mz=self.stats["new_mz"],
                calibration_mz_error=self.stats["post_dmz"],
                mz_error_diff=abs(self.stats["post_dmz"]) - abs(self.stats["pre_dmz"]),
                calibrant_to_tic=calibrant_to_tic,
            )
            calibration_inaccurate = (
                abs(calibration_df["calibration_mz_error"])
                > self.params.mz_error_tolerance
            ).any()
            if calibration_inaccurate:
                self.warning = "Calibration inaccurate"
            self.stats = calibration_df.to_dict("records")
            summary_row = self._get_summary_row(calibration_df)
            self.stats.append(summary_row)

            await send_progress_user_notification(self.notification, 0.95)
        else:
            self.fit_result = None
            self.stats = good_matches_df.to_dict("records")
            self.warning = "Not enough calibration peaks"

    async def apply(self, fit: dict):
        """Applies the m/z calibration fit to the sample file.
        NOTE: fit is passed externally since fit() and apply() used in different controllers
        and the instance of TofCalibrationHandler is not passed between them."""
        fit_mode = fit["mode"]
        fit_parameters = fit["par"]

        nbr_samples = m_compute.get_sum_signal(self.filename).size
        tof = np.arange(nbr_samples)
        new_mz_axis = tof_to_mass(tof, fit_mode, fit_parameters)
        new_mz_range = new_mz_axis[0], new_mz_axis[-1]

        runtime.logger.info(f"Calibrating file: {self.filename}")
        sample_file_type = m_name.get_sample_file_type(self.filename)
        m_io.update_props(self.filename, {"range": new_mz_range, "mz_calibration": fit})
        if sample_file_type == "tof_zarr":
            m_io.update_zarr_array_coord(self.filename, "signal", "mz", new_mz_axis)

        # Update m/z axis for all sum signals
        sample_data_path = m_name.parse_path_from_item_filename(self.filename)
        sample_file_vars = m_io.get_file_data_vars(sample_data_path)
        for sum_signal_var in sample_file_vars:
            if sum_signal_var.startswith("sum_signal"):
                m_io.update_zarr_array_coord(
                    self.filename, sum_signal_var, "mz", new_mz_axis
                )

        try:
            peak_tofs = m_io.load_coord(self.filename, "peak_areas", "tof")
            new_peak_mz = tof_to_mass(peak_tofs, fit_mode, fit_parameters)
            m_io.update_zarr_array_coord(self.filename, "peak_areas", "mz", new_peak_mz)
            m_io.update_zarr_array_coord(
                self.filename, "peak_heights", "mz", new_peak_mz
            )
        except PathNotFoundError:
            runtime.logger.warning(
                f"Peak_areas/heights not found in {self.filename}, "
                "thus their m/z coordinates were not updated."
            )
        return new_mz_axis


class OrbiCalibrationHandler(BaseCalibrationHandler):
    @api_controller()
    async def fit(self):
        """Fit the m/z calibration for an Orbitrap instrument."""
        match_params = OrbiMatchParams(
            mz_tolerance=self.params.mz_error_tolerance,
            peak_min_intensity=self.params.peak_intensity_min,
        )
        match_params.min_isotope_abundance = self.params.isotope_abundance_min

        await send_progress_user_notification(self.notification, 0.25)

        match_isotope_df, good_matches_df = await self._match_calibration_compounds(
            match_params
        )

        await send_progress_user_notification(self.notification, 0.75)

        if good_matches_df.empty:
            self.warning = "No calibration peaks found"
            return

        target_mzs = good_matches_df["mz"].to_numpy()
        observed_mzs = good_matches_df["sample_peak_mz"].to_numpy()

        old_factor_scaling = np.median(target_mzs / observed_mzs)
        old_factor = self._get_old_factor()
        calibration_factor = old_factor * old_factor_scaling
        # Store all factors at the time of fitting for unit testing
        self.fit_result = {
            "mode": "one-point",
            "par": {
                "old_factor": old_factor,
                "old_factor_scaling": old_factor_scaling,
                "calibration_factor": calibration_factor,
            },
        }

        # Show stats relative to the original m/z values
        self.stats = {
            "mz": observed_mzs,
            "new_mz": observed_mzs * calibration_factor,
            "pre_dmz": 1e6 * (observed_mzs - target_mzs) / target_mzs,
            "post_dmz": 1e6
            * (observed_mzs * old_factor_scaling - target_mzs)
            / target_mzs,
        }

        _, tic_per_scan = m_compute.get_tic_per_scan(self.filename)
        tic = np.sum(tic_per_scan)
        calibrant_signal_intensity = good_matches_df["sample_peak_intensity"]
        calibrant_to_tic = calibrant_signal_intensity / tic

        calibration_df = good_matches_df.copy().assign(
            calibration_mz=self.stats["new_mz"],
            calibration_mz_error=self.stats["post_dmz"],
            mz_error_diff=abs(self.stats["post_dmz"]) - abs(self.stats["pre_dmz"]),
            calibrant_to_tic=calibrant_to_tic,
        )
        calibration_inaccurate = (
            abs(calibration_df["calibration_mz_error"]) > self.params.mz_error_tolerance
        ).any()
        if calibration_inaccurate:
            self.warning = "Calibration inaccurate"

        self.stats = calibration_df.to_dict("records")
        summary_row = self._get_summary_row(calibration_df)
        self.stats.append(summary_row)

        await send_progress_user_notification(self.notification, 0.95)

    async def apply(self, fit: dict):
        """Applies the m/z calibration fit to the sample file.
        M/z scales for existing signals and peaks are scaled based on a new calibration.
        A new calibration factor is stored for new sum signals and
        signals to be generated later.
        """
        fit_parameters = fit["par"]
        old_factor_scaling = fit_parameters["old_factor_scaling"]
        if self._is_calibration_already_applied(fit):
            runtime.logger.info("Same calibration already applied; skipping.")
            return m_io.load_coord(self.filename, "sum_signal", "mz")

        runtime.logger.info(f"Calibrating file: {self.filename}")

        # Update m/z axis for all existing sum signals
        sample_data_path = m_name.parse_path_from_item_filename(self.filename)
        sample_file_vars = m_io.get_file_data_vars(sample_data_path)
        for var in sample_file_vars:
            if var.startswith("sum_signal"):
                new_mz_axis = (
                    m_io.load_coord(self.filename, var, "mz") * old_factor_scaling
                )
                m_io.update_zarr_array_coord(self.filename, var, "mz", new_mz_axis)

        # Update m/z axis for signal and peak arrays if they exist
        sample_file_type = m_name.get_sample_file_type(self.filename)
        if sample_file_type == "orbi_zarr":
            new_signal_mz = (
                m_io.load_array(self.filename, "signal").mz.values * old_factor_scaling
            )
            m_io.update_zarr_array_coord(self.filename, "signal", "mz", new_signal_mz)
        try:
            new_peak_mz = (
                m_io.load_coord(self.filename, "peak_areas", "mz") * old_factor_scaling
            )
            m_io.update_zarr_array_coord(self.filename, "peak_areas", "mz", new_peak_mz)
            m_io.update_zarr_array_coord(
                self.filename, "peak_heights", "mz", new_peak_mz
            )
        except PathNotFoundError:
            runtime.logger.warning(
                f"Peak_areas/heights not found in {self.filename}, "
                "thus their m/z coordinates were not updated."
            )

        # Remove excessive items
        fit["par"].pop("old_factor", None)
        fit["par"].pop("old_factor_scaling", None)
        # Update sample file properties
        full_sum_signal_mz = m_io.load_coord(self.filename, "sum_signal", "mz")
        new_mz_range = full_sum_signal_mz[0], full_sum_signal_mz[-1]
        m_io.update_props(self.filename, {"range": new_mz_range, "mz_calibration": fit})

        return full_sum_signal_mz

    def _get_old_factor(self) -> float:
        """Retrieve the old calibration factor from the file properties if exists."""
        props = m_io.read_props(self.filename)
        old_mz_calibration = props["mz_calibration"]
        if old_mz_calibration is None:
            old_factor = 1.0
        else:
            old_factor = old_mz_calibration["par"]["calibration_factor"]
        return old_factor

    def _is_calibration_already_applied(self, fit: dict) -> bool:
        """Check if the calibration has already been applied."""
        props = m_io.read_props(self.filename)
        existing_calibration = props["mz_calibration"]
        if (
            existing_calibration
            and existing_calibration["par"]["calibration_factor"]
            == fit["par"]["calibration_factor"]
        ):
            return True
        return False


def get_calibration_handler(
    filename: str, calibration_params: CalibrationFitParams, notifications: object
) -> BaseCalibrationHandler:
    instrument_type = m_name.get_instrument_type(filename)
    match instrument_type:
        case "tof":
            return TofCalibrationHandler(filename, calibration_params, notifications)
        case "orbi":
            return OrbiCalibrationHandler(filename, calibration_params, notifications)
        case _:
            raise ValueError(f"Unsupported instrument type: {instrument_type}")
