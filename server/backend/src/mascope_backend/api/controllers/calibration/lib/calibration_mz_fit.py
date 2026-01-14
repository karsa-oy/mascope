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

from mascope_match.compute.isotopes import (
    calculate_match_stats,
)
from mascope_match.params import (
    TofMatchParams,
    OrbiMatchParams,
    BaseMatchParams,
    UnmatchedIsotopeParams,
)
from mascope_backend.api.lib.api_features import (
    api_controller,
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
    OrbiCalibrationParams,
    TofCalibrationParams,
    MzCalibrationParams,
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

    async def _match_calibration_compounds(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Match calibration compounds in the sample file."""
        target_compounds_result = await get_target_compound_in_target_collection(
            target_collection_id=self.params.calibration_collection_id,
        )
        target_compound_ids = [
            item["target_compound_id"] for item in target_compounds_result["data"]
        ]

        instrument_type = m_name.get_instrument_type(self.filename)
        match instrument_type:
            case "tof":
                isotope_resolution = "LOW"
            case "orbi":
                isotope_resolution = "HIGH"

        target_isotopes_result = await get_target_isotopes(
            target_compound_ids=target_compound_ids,
            ionization_mechanism_ids=self.params.ionization_mechanism_ids,
            resolution=isotope_resolution,
        )
        target_isotopes_df = pd.DataFrame(target_isotopes_result["data"])

        peaks = await self._load_peaks(
            target_mzs=target_isotopes_df.mz,
        )

        match_df = target_isotopes_df.copy().assign(
            sample_peak_id=np.nan,
            sample_peak_mz=np.nan,
            sample_peak_intensity=np.nan,
            sample_peak_intensity_relative=np.nan,
            match_abundance_error=np.nan,
            match_isotope_similarity=np.nan,
            match_mz_error=np.nan,
            match_score=np.nan,
            sample_peak_tof=np.nan,
            matched_peak_idx=np.nan,
        )

        averaged_peaks = peaks.mean(dim="time")
        averaged_peaks_dict = {
            "mz": averaged_peaks.mz.values,
            "tof": averaged_peaks.tof.values,
            "intensity": averaged_peaks.values,
        }
        match_df = match_df.apply(
            self._match_max_in_range,
            args=(averaged_peaks_dict,),
            axis=1,
        ).reset_index(drop=True)

        matched_mask = ~match_df["sample_peak_mz"].isna()
        if matched_mask.any():
            match_df = match_df[matched_mask]
            match_df = calculate_match_stats(match_df, peaks)
        else:
            # No calibration peaks matched
            # Return empty DataFrame for both match_df and good_matches_df
            return match_df.iloc[0:0], match_df.iloc[0:0]

        # Ensure correct dtypes for match_df columns to avoid warnings
        match_df = match_df.astype(
            {
                "sample_peak_id": "string",
                "sample_peak_mz": "float64",
                "sample_peak_intensity": "float64",
                "sample_peak_intensity_relative": "float64",
                "match_abundance_error": "float64",
                "match_isotope_similarity": "float64",
                "match_mz_error": "float64",
                "match_score": "float64",
                "sample_peak_tof": "float64",
            }
        )
        # Fill np.nan with serializable defaults for unmatched isotopes
        default_unmatched_params = UnmatchedIsotopeParams().model_dump()
        match_df = match_df.fillna(default_unmatched_params)
        # Matches contain duplicates for every ionization mechanism, we drop them
        match_df = (
            match_df.sort_values(by=["sample_peak_mz", "target_ion_id"])
            .drop_duplicates(subset="sample_peak_mz", keep="first")
            .reset_index(drop=True)
        )

        good_matches_df = match_df[
            (match_df.relative_abundance >= self.params.isotope_abundance_min)
            & (match_df.sample_peak_intensity >= self.params.peak_intensity_min)
            & (abs(match_df.match_mz_error) <= self.params.refine_window)
            & (match_df.match_score >= self.params.match_score_min)
        ]

        return match_df, good_matches_df

    async def _load_peaks(
        self,
        target_mzs: pd.Series,
    ):
        """Load peak timeseries of the potential calibration peaks.

        :param target_mzs: Series of target m/z values to be matched against the sample peaks.
        :type target_mzs: pd.Series
        :return: DataArray containing detected peaks with their m/z, intensity, and time information.
        :rtype: xarray.DataArray
        """
        target_mzs = np.asarray(target_mzs)
        all_mzs = m_io.load_coord(self.filename, "peak_timeseries", "mz")
        mz_mask = np.any(
            np.abs(all_mzs[:, None] - target_mzs[None, :])
            <= self.params.refine_window * 1e-6 * target_mzs[None, :],
            axis=1,
        )
        potential_calibration_mzs = all_mzs[mz_mask]

        peak_timeseries = await m_compute.load_peak_timeseries(
            self.filename, potential_calibration_mzs
        )

        # Reverse compatibility with older zarr files
        sample_file_type = m_name.get_sample_file_type(self.filename)
        if sample_file_type in ["orbi_zarr", "tof_zarr"]:
            peak_timeseries = peak_timeseries.dropna(dim="mz", how="all")

        peaks = self._parse_and_filter_peaks(peak_timeseries)

        return peaks

    def _parse_and_filter_peaks(self, peak_timeseries: "xarray.Dataset") -> "Dataarray":  # type: ignore # noqa: F821
        """
        Parse and filter peaks from the peak timeseries.
        Only peaks with positive intensities across all time points are retained.
        In case of multipolarity files, the polarity of the peaks is considered.

        :param peak_timeseries: Timeseries dataset of peaks.
        :type peak_timeseries: xarray.Dataset
        :return: Filtered DataArray of peaks with positive intensities.
        :rtype: xarray.DataArray
        """
        instrument_type = m_name.get_instrument_type(self.filename)
        match instrument_type:
            case "orbi":
                peaks = peak_timeseries.peak_heights
            case "tof":
                peaks = peak_timeseries.peak_areas

        is_multipolarity_file = np.unique(peak_timeseries.polarity.values).size > 1
        if is_multipolarity_file:
            # Check positivity for the polarity of the peaks
            # All target peaks should have the same polarity
            polarity = peak_timeseries.polarity.values[0]
            timestamps = m_compute.get_scan_timestamps(self.filename, polarity=polarity)

            positive_mask = (
                peaks.sel(time=timestamps, method="nearest").values > 0
            ).all(axis=peaks.get_axis_num("time"))
        else:
            # Skip polarity selection, check positivity across all time points
            positive_mask = (peaks.values > 0).all(axis=peaks.get_axis_num("time"))

        filtered_peaks = peaks.sel(mz=peaks.mz.values[positive_mask])

        return filtered_peaks

    def _match_max_in_range(
        self,
        isotope_row: pd.Series,
        peaks: dict,  # type: ignore # noqa: F821
    ):
        """Match the isotope to the peak with the highest intensity within the m/z tolerance range."""
        target_mz = isotope_row["mz"]
        mz_tolerance = self.params.refine_window * 1e-6 * target_mz

        in_range_mask = np.abs(peaks["mz"] - target_mz) <= mz_tolerance
        mz_in_range = peaks["mz"][in_range_mask]
        tof_in_range = peaks["tof"][in_range_mask]
        intensity_in_range = peaks["intensity"][in_range_mask]

        if np.any(in_range_mask):
            max_peak_idx = np.argmax(intensity_in_range)
            isotope_row["sample_peak_mz"] = mz_in_range[max_peak_idx]
            isotope_row["sample_peak_tof"] = tof_in_range[max_peak_idx]
            isotope_row["sample_peak_intensity"] = intensity_in_range[max_peak_idx]
            isotope_row["matched_peak_idx"] = max_peak_idx

        return isotope_row

    def _get_summary_row(self, calibration_df):
        match_mz_error = abs(calibration_df["match_mz_error"]).mean()
        calibration_mz_error = abs(calibration_df["calibration_mz_error"]).mean()
        mz_error_diff = abs(match_mz_error - calibration_mz_error)
        calibrant_to_tic = sum(calibration_df["calibrant_to_tic"])
        return {
            "match_mz_error": match_mz_error,
            "calibration_mz_error": calibration_mz_error,
            "mz_error_diff": mz_error_diff,
            "calibrant_to_tic": calibrant_to_tic,
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
        await send_progress_user_notification(self.notification, 0.25)

        _, tic_per_scan = m_compute.get_tic_per_scan(self.filename)
        tic = np.sum(tic_per_scan)
        if tic < self.params.tic_threshold:
            self.warning = "TIC is too low! Check ionization device."
            return self.fit_result, self.stats, self.error, self.warning

        await send_progress_user_notification(self.notification, 0.35)

        match_isotope_df, good_matches_df = await self._match_calibration_compounds()

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

        if n_relevant_isotopes >= 3 and len(good_matches_df) >= 3:
            self.fit_result, self.stats = mz_calibrate(
                good_matches_df["sample_peak_tof"],
                good_matches_df["sample_peak_mz"],
                good_matches_df["mz"],
            )
            zero_coefficient = any([coef == 0 for coef in self.fit_result["par"]])
            if zero_coefficient:
                self.fit_result = None
                self.stats = good_matches_df.to_dict("records")
                self.error = "Calibration failed"
                return

            calibration_df = good_matches_df.copy().assign(
                calibration_mz=self.stats["new_mz"],
                calibration_mz_error=self.stats["post_dmz"],
                mz_error_diff=abs(self.stats["post_dmz"]) - abs(self.stats["pre_dmz"]),
                calibrant_to_tic=calibrant_to_tic,
            )
            self.stats = calibration_df.to_dict("records")
            summary_row = self._get_summary_row(calibration_df)
            self.stats.append(summary_row)

            isotopes_from_single_ion = len(good_matches_df.target_ion_id.unique()) == 1
            mz_err_too_high = (
                abs(summary_row["calibration_mz_error"])
                > self.params.mz_error_tolerance
            )
            calibration_inaccurate = mz_err_too_high or isotopes_from_single_ion
            if calibration_inaccurate:
                self.warning = "Calibration inaccurate"

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
            peak_tofs = m_io.load_coord(self.filename, "peak_timeseries", "tof")
            new_peak_mz = tof_to_mass(peak_tofs, fit_mode, fit_parameters)
            m_io.update_zarr_array_coord(
                self.filename, "peak_timeseries", "mz", new_peak_mz
            )
        except PathNotFoundError:
            runtime.logger.warning(
                f"peak_timeseries not found in {self.filename}, "
                "thus their m/z coordinates were not updated."
            )
        return new_mz_axis


class OrbiCalibrationHandler(BaseCalibrationHandler):
    @api_controller()
    async def fit(self):
        """Fit the m/z calibration for an Orbitrap instrument."""
        await send_progress_user_notification(self.notification, 0.25)

        match_isotope_df, good_matches_df = await self._match_calibration_compounds()

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
            "new_mz": observed_mzs * old_factor_scaling,
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

        calibration_inaccurate = np.all(
            np.abs(calibration_df["calibration_mz_error"])
            > self.params.mz_error_tolerance
        )
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
                m_io.load_coord(self.filename, "peak_timeseries", "mz")
                * old_factor_scaling
            )
            m_io.update_zarr_array_coord(
                self.filename, "peak_timeseries", "mz", new_peak_mz
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


def calibration_params_factory(filename: str, **kwargs) -> MzCalibrationParams:
    instrument_type = m_name.get_instrument_type(filename)
    match instrument_type:
        case "tof":
            return TofCalibrationParams(**kwargs)
        case "orbi":
            return OrbiCalibrationParams(**kwargs)
        case _:
            raise ValueError(f"Unknown instrument type: {instrument_type}")
