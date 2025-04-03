import pandas as pd
import numpy as np
from mascope_backend.api.new.match.params.schema import (
    DEFAULT_MIN_ISOTOPE_ABUNDANCE,
)
from mascope_file.io import load_array, load_file
from mascope_file.name import get_instrument_type

from mascope_signal.compute import get_sum_signal
from mascope_signal.peak import calculate_signal_area, detect_peaks

from mascope_chem.mz import match_mz

from mascope_backend.db.id import gen_id
from mascope_backend.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)
from mascope_backend.api.lib.api_features import (
    api_controller,
)
from mascope_backend.api.controllers.match.isotopes.match_isotopes_controller import (
    create_match_isotopes,
)
from mascope_backend.api.controllers.match.interferences.match_interferences_controller import (
    create_match_interferences,
)
from mascope_backend.api.models.match.match_pydantic_model import (
    MatchComputeSample,
)
from mascope_backend.api.models.match.interferences.match_interferences_pydantic_model import (
    MatchInterferenceBase,
)
from mascope_backend.api.models.match.isotopes.match_isotopes_pydantic_model import (
    MatchIsotopeBase,
)
from mascope_backend.api.new.instrument_configs.lib import (
    read_instrument_functions,
)

from mascope_backend.runtime import runtime

# -------------------------------------------------------------------
# Isotope level
# -------------------------------------------------------------------


async def compute_match_isotopes(
    filename, target_isotopes_df, min_isotope_abundance, instrument_functions=None
):
    """
    Computes matches for specified target isotopes within a sample file.

    This function identifies the best matching peaks within the sample spectrum for each target isotope based on
    their m/z values. It computes match statistics such as match score, m/z error, and isotope correlation.

    Steps:
    1. Load peaks from the sample file and prepare the data for matching.
    2. MatchIsotope each target isotope to the closest peak within a predefined m/z tolerance window.
    3. Compute match statistics such as isotope correlations, m/z errors, and match score.
    4. Return a DataFrame containing the match details for each target isotope.

    :param filename: Path to the sample file to be analyzed for matches.
    :type filename: str
    :param target_isotopes_df: DataFrame containing target isotopes with their m/z values and other properties.
    :type target_isotopes_df: pd.DataFrame
    :param min_isotope_abundance: Minimum relative abundance threshold for isotopes to be considered in matching.
    :type min_isotope_abundance: float
    :param instrument_functions: Optional tuple containing peak shape details and a resolution function R.
    :type instrument_functions: tuple(dict, function), optional
    :return: DataFrame with details of the matches found for each target isotope.
    :rtype: pd.DataFrame
    :raises RuntimeError: If an error occurs during the matching process.

    Notes:
        - Matching is done on isotope-level. Ion, compound and collection level matches are aggregated from
        isotope-level matches on read sample operation; see the samples_controller.py for this aggregation.

    TODO min_isotope_abundance will be passed from the match_params
    """
    try:
        # Check if instrument functions were passed
        if instrument_functions is None:
            instrument_functions = await read_instrument_functions(filename)
        instrument_type = get_instrument_type(filename)

        # Filter isotopes below threshold and with incorrect resolution
        resolution_type = "LOW" if instrument_type == "tof" else "HIGH"
        query = "relative_abundance >= @min_isotope_abundance and resolution == @resolution_type"
        target_isotopes_df = target_isotopes_df.query(query).reset_index(drop=True)

        # Step 1: - Load or detect peaks
        # Find peaks and write to file
        u_list = list(np.unique(np.round(target_isotopes_df.mz)))

        # Assign peak fitting threshold depending on the instrument type
        # Correct intrument type unsured by get_instrument_type
        if instrument_type == "orbi":
            threshold = 0.8
        if instrument_type == "tof":
            threshold = 0.9
        await detect_peaks(
            filename,
            instrument_functions,
            threshold,
            u_list,
            if_exists="append",
            instrument_type=instrument_type,
        )

        runtime.logger.debug("Start matching")

        if instrument_type == "orbi":
            peaks = load_array(filename, "peak_heights").peak_heights
        if instrument_type == "tof":
            peaks = load_array(filename, "peak_areas").peak_areas

        # Step 2: - Prepare data
        # init match df from target isotopes
        match_isotope_df = target_isotopes_df.copy().assign(
            match_isotope_id=np.nan,
            sample_peak_id=np.nan,
            sample_peak_mz=np.nan,
            sample_peak_area=np.nan,
            sample_peak_area_relative=np.nan,
            match_abundance_error=np.nan,
            match_isotope_correlation=np.nan,
            match_mz_error=np.nan,
            match_score=np.nan,
        )

        runtime.logger.debug("Parse peak data")
        peak_mzs = peaks.mz.values
        peak_areas = peaks.sum(dim="time").compute().values
        peak_tofs = peaks.tof.values
        peak_sorting = np.argsort(peak_mzs)

        # Step 3: - Perform matching

        def match(row):
            # Get all peaks within unit mass window
            mz_tolerance = 0.5
            target_mz = row.mz
            match_indeces, _ = match_mz(
                target_mz, peak_mzs[peak_sorting], tolerance=mz_tolerance
            )
            # Find closest match
            for match_index in match_indeces:
                # get match peak
                peak_index = peak_sorting[match_index]
                peak_mz = peak_mzs[peak_index]
                peak_area = peak_areas[peak_index]
                # check current best match
                best_match = row.sample_peak_id
                if not np.isnan(best_match):
                    prev_mz_err = np.abs(row.sample_peak_mz - target_mz)
                    new_mz_err = np.abs(peak_mz - target_mz)
                    if new_mz_err > prev_mz_err:
                        continue
                # save match
                row["match_isotope_id"] = gen_id(length=32)
                row["sample_peak_id"] = peak_index
                row["sample_peak_mz"] = peak_mz
                row["sample_peak_tof"] = peak_tofs[int(peak_index)]
                row["sample_peak_area"] = peak_area
            return row

        match_isotope_df = (
            match_isotope_df.apply(match, axis=1)
            .dropna(subset=["sample_peak_mz"])
            .reset_index()
        )

        # Step 4: - Calculate match stats

        # calculate isotope ratios
        # sum matched sample peak heights for each ion
        ion_level_peak_sums = match_isotope_df.groupby(
            ["target_ion_id"], as_index=False
        )["sample_peak_area"].sum()
        # join sums back to the isotope level
        isotope_level_peak_sums = pd.merge(
            match_isotope_df,
            ion_level_peak_sums.rename(
                columns={"sample_peak_area": "sample_peak_area_sum"}
            ),
            on=["target_ion_id"],
            how="left",
        )

        # compute relative peak heights
        match_isotope_df.loc[:, "sample_peak_area_relative"] = (
            match_isotope_df["sample_peak_area"]
            / isotope_level_peak_sums["sample_peak_area_sum"]
        )
        # calculate isotope ratio errors
        match_isotope_df.loc[:, "match_abundance_error"] = match_isotope_df[
            "relative_abundance"
        ] * (
            match_isotope_df["sample_peak_area_relative"]
            - match_isotope_df["relative_abundance"]
        )
        # calculate isotope correlations
        match_isotope_df = match_isotope_df.groupby(
            ["target_ion_id"], group_keys=False
        ).apply(
            lambda ion_group: (
                ion_group.assign(
                    match_isotope_correlation=(
                        np.corrcoef(
                            np.array(
                                [
                                    peaks.sel(mz=peak_mz, method="nearest")
                                    for peak_mz in ion_group["sample_peak_mz"]
                                ]
                            )
                        )[0, 1]
                        if len(ion_group) > 1
                        else 1
                    )
                )
            )
        )
        match_isotope_df["match_isotope_correlation"] = match_isotope_df[
            "match_isotope_correlation"
        ].fillna(value=0)

        # calculate mz errors
        match_isotope_df.loc[:, "match_mz_error"] = (
            1e6
            * (match_isotope_df["sample_peak_mz"] - match_isotope_df["mz"])
            / match_isotope_df["mz"]
        )

        def score(row):
            row["match_score"] = (1 - abs(row.match_abundance_error)) * max(
                0, (1 - 1e-2 * abs(row.match_mz_error))
            )
            return row

        match_isotope_df = match_isotope_df.apply(
            score, axis=1, result_type="broadcast"
        )
        return match_isotope_df
    except Exception as e:
        error_message = f"Computing matches failed: {e}"
        raise RuntimeError(error_message)


async def compute_match_interferences(
    filename,
    target_isotopes_df,
) -> pd.DataFrame:
    """
    Computes match interferences for a given sample file based on specified target isotopes.

    This function calculates the raw intensities for each target isotope within the specified mass-to-charge (m/z) range,
    which are used to identify potential interferences in the sample's spectrum. It involves loading the sample file data,
    summing up the spectrum, and then computing the raw intensities for the target isotopes.

    Steps:
    1. Load the sample file and compute the summed spectrum across all time points.
    2. For each target isotope, calculate the raw intensity within a defined m/z range around the target m/z value.

    :param filename: Path to the sample file from which to compute interferences.
    :type filename: str
    :param target_isotopes_df: DataFrame containing the target isotopes and their m/z values.
    :type target_isotopes_df: pd.DataFrame
    :return: DataFrame with computed interferences for each target isotope.
    :rtype: pd.DataFrame
    :raises RuntimeError: If an error occurs during the computation process.
    """
    try:
        # Step 1: Load the sample file and compute the summed spectrum
        sum_spectrum = get_sum_signal(filename)
        instrument_type = get_instrument_type(filename)

        # Read instrument resolution function
        _, R = await read_instrument_functions(filename=filename)

        # Step 2: Initialize DataFrame for interferences and compute raw intensities for each target mz
        isotope_interference_df = target_isotopes_df.copy().assign(
            sample_peak_interference=np.nan,
        )

        # Read sample interval if dealing with TOF, default 0.25 for backwards compatibility
        sample_interval = (
            (load_file(filename, vars=[]).attrs["props"].get("sample_interval", 0.25))
            if instrument_type == "tof"
            else None
        )

        def calc_raw_intensity(row):
            target_mz = row.mz
            dmz = (target_mz / R(target_mz)) / 2  # hwhm
            if instrument_type == "tof":
                # For the TOF, calculate signal area in the mz range
                target_raw_intensity = calculate_signal_area(
                    filename,
                    mz_min=target_mz - dmz,
                    mz_max=target_mz + dmz,
                    sum_spectrum=sum_spectrum,
                    sample_interval=sample_interval,
                )
            else:
                # For the Orbitrap, calculate signal maximum intensity in the mz range
                sum_spectrum_slice = sum_spectrum.sel(
                    mz=slice(target_mz - dmz, target_mz + dmz)
                )
                if sum_spectrum_slice.shape[0] == 0:
                    target_raw_intensity = 0
                else:
                    target_raw_intensity = (
                        sum_spectrum_slice.max(dim="mz").compute().item()
                    )
            row["match_interference_id"] = gen_id(length=32)
            row["sample_peak_interference"] = target_raw_intensity
            return row

        isotope_interference_df = isotope_interference_df.apply(
            calc_raw_intensity, axis=1
        )

        return isotope_interference_df
    except Exception as e:
        error_message = f"Computing match interferences failed: {e}"
        raise RuntimeError(error_message)


# -------------------------------------------------------------------
# Sample level
# -------------------------------------------------------------------


@api_controller()
async def compute_and_create_sample_match_isotope_data(
    sample: MatchComputeSample,
    target_isotopes_df,
    notification: UserNotification = None,
):
    """
    Computes matc isotopes and match interferences for a given sample against a set of target isotopes.

    It updates the computation progress if progress properties are provided. Match isotopes and interferences are then saved to the database.

    Steps:
    1. Unpack sample parameters including sample item ID and filename.
    2. Compute match interferences for the sample using the provided target isotopes.
    3. Compute match isotopes for the sample using the provided target isotopes.
    4. Save computed match interferences and match isotopes to the database, ensuring no duplication.
    5. Update computation progress at each significant step if progress tracking is enabled.

    :param sample: Contains details of the sample for which match isotopes are being computed, including sample item ID and filename.
    :type sample: MatchComputeSample
    :param target_isotopes_df: A DataFrame containing target isotope information for match computation.
    :type target_isotopes_df: DataFrame
    :param notification: Optional notification for sending progress user notifications of match computation.
    :type notification: UserNotification, optional
    :raises RuntimeError: If no match interferences or match isotopes are found during computation.
    """
    # Step 1: Unpack the sample parameters for ease of use
    sample_item_id = sample.sample_item_id
    filename = sample.filename

    #  Sent progress user notificaton if notification is provided
    if notification:
        await send_progress_user_notification(notification, 0.25)

    # Step 2: Compute match interferences for the given sample and target isotopes.
    runtime.logger.info(f"Computing match interferences for file: {filename}")
    match_interference_df = await compute_match_interferences(
        filename, target_isotopes_df
    )
    if match_interference_df.empty:
        raise RuntimeError("No match interferences found")
    # Send progress user notificaton after computing interferences
    if notification:
        await send_progress_user_notification(notification, 0.5)

    # Step 3: Compute match isotopes for the given sample and target isotopes.
    runtime.logger.info(f"Computing match isotopes for file: {filename}")

    match_isotope_df = await compute_match_isotopes(
        filename=filename,
        target_isotopes_df=target_isotopes_df,
        min_isotope_abundance=DEFAULT_MIN_ISOTOPE_ABUNDANCE,
    )
    if match_isotope_df.empty:
        raise RuntimeError("No match isotopes found")
    # Send progress user notificaton after computing match isotopes
    if notification:
        await send_progress_user_notification(notification, 0.75)

    # Step 4: Save to the database computed match interferences and isotopes if any were found
    match_interference_df["sample_item_id"] = sample_item_id
    match_isotope_df["sample_item_id"] = sample_item_id

    # Convert the DataFrame to a list of Pydantic models
    match_interferences = [
        MatchInterferenceBase(**row)
        for row in match_interference_df.to_dict(orient="records")
    ]
    match_isotopes = [
        MatchIsotopeBase(**row) for row in match_isotope_df.to_dict(orient="records")
    ]

    await create_match_interferences(match_interferences)
    await create_match_isotopes(match_isotopes)

    # Send progress user notificaton indicating completion of compute_and_create_sample_match_isotope_data process
    if notification:
        await send_progress_user_notification(notification, 0.95)
