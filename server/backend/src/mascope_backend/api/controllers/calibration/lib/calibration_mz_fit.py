"""
Functionalities related to the m/z fitting calibration processes.
"""

import numpy as np
import pandas as pd
from zarr.errors import PathNotFoundError

from mascope_tofwerk.calibration import mz_calibrate, tof_to_mass

from mascope_file.io import load_coord, update_props, update_zarr_array_coord
from mascope_file.name import get_sample_file_type, get_instrument_type

from mascope_signal.compute import get_sum_signal, get_tic_per_scan

from mascope_match import compute_match_isotopes
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
from mascope_backend.api.new.match.params import TofMatchParams
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
        await send_progress_user_notification(self.notification, 0.25)

        _, tic_per_scan = get_tic_per_scan(self.filename)
        tic = np.sum(tic_per_scan)
        if tic < self.params.tic_threshold:
            self.warning = "TIC is too low! Check ionization device."
            return self.fit_result, self.stats, self.error, self.warning

        await send_progress_user_notification(self.notification, 0.35)

        # Compute matches for calibration compounds
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

        match_params = TofMatchParams(
            mz_tolerance=self.params.mz_error_tolerance,
            peak_min_intensity=self.params.peak_intensity_min,
        )
        match_params.min_isotope_abundance = self.params.isotope_abundance_min

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
        ]
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
            summary_row = {
                "match_mz_error": abs(calibration_df["match_mz_error"]).mean(),
                "calibration_mz_error": abs(
                    calibration_df["calibration_mz_error"]
                ).mean(),
                "mz_error_diff": sum(calibration_df["mz_error_diff"]),
                "calibrant_to_tic": sum(calibration_df["calibrant_to_tic"]),
            }
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

        nbr_samples = get_sum_signal(self.filename).size
        tof = np.arange(nbr_samples)
        new_mz_axis = tof_to_mass(tof, fit_mode, fit_parameters)
        new_mz_range = new_mz_axis[0], new_mz_axis[-1]

        runtime.logger.info(f"Calibrating file: {self.filename}")
        sample_file_type = get_sample_file_type(self.filename)
        update_props(self.filename, {"range": new_mz_range, "mz_calibration": fit})
        if sample_file_type == "tof_zarr":
            update_zarr_array_coord(self.filename, "signal", "mz", new_mz_axis)
        update_zarr_array_coord(self.filename, "sum_signal", "mz", new_mz_axis)

        try:
            peak_tofs = load_coord(self.filename, "peak_areas", "tof")
            new_peak_mzs = new_mz_axis[peak_tofs.astype(int)]
            update_zarr_array_coord(self.filename, "peak_areas", "mz", new_peak_mzs)
            update_zarr_array_coord(self.filename, "peak_heights", "mz", new_peak_mzs)
        except PathNotFoundError:
            runtime.logger.warning(
                f"Peak_areas/heights not found in {self.filename}, "
                "thus their m/z coordinates were not updated."
            )
        return new_mz_axis


class OrbiCalibrationHandler(BaseCalibrationHandler):

    async def fit(self):
        self.warning = "Calibration fitting not implemented for Orbitrap instruments."
        pass

    async def apply(self, fit: dict):
        self.warning = (
            "Calibration application not implemented for Orbitrap instruments."
        )
        pass


def get_calibration_handler(
    filename: str, calibration_params: CalibrationFitParams, notifications: object
) -> BaseCalibrationHandler:
    instrument_type = get_instrument_type(filename)
    match instrument_type:
        case "tof":
            return TofCalibrationHandler(filename, calibration_params, notifications)
        case "orbi":
            return OrbiCalibrationHandler(filename, calibration_params, notifications)
        case _:
            raise ValueError(f"Unsupported instrument type: {instrument_type}")
