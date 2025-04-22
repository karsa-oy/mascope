import pandas as pd
from mascope_match import (
    compute_match_isotopes,
    compute_match_interferences,
)
from mascope_backend.api.new.match.params.schema import (
    DEFAULT_MIN_ISOTOPE_ABUNDANCE,
)
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


@api_controller()
async def compute_and_create_sample_match_isotope_data(
    sample: MatchComputeSample,
    target_isotopes_df: pd.DataFrame,
    notification: UserNotification | None = None,
) -> dict[str, pd.DataFrame]:
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
    :type notification: UserNotification | None
    :return: Dictionary containing match_isotopes and match_interferences DataFrames
    :rtype: dict[str, pd.DataFrame]
    """
    # Step 1: Unpack the sample parameters for ease of use
    sample_item_id = sample.sample_item_id
    filename = sample.filename
    polarity = sample.polarity
    sample_item_name = sample.sample_item_name

    # Get instrument functions for filename
    instrument_functions = await read_instrument_functions(filename)

    #  Sent progress user notificaton if notification is provided
    if notification:
        await send_progress_user_notification(notification, 0.25)

    # Step 2: Compute match interferences for the given sample and target isotopes.
    runtime.logger.info(f"Computing match interferences for file: {filename}")
    match_interference_df = await compute_match_interferences(
        filename=filename,
        target_isotopes_df=target_isotopes_df,
        instrument_functions=instrument_functions,
    )
    if match_interference_df.empty:
        runtime.logger.warning(
            f"No match interferences found for sample '{sample_item_name}'"
        )

    # Send progress user notificaton after computing interferences
    if notification:
        await send_progress_user_notification(notification, 0.5)

    # Step 3: Compute match isotopes for the given sample and target isotopes.
    runtime.logger.info(f"Computing match isotopes for file: {filename}")

    match_isotope_df = await compute_match_isotopes(
        filename=filename,
        target_isotopes_df=target_isotopes_df,
        min_isotope_abundance=DEFAULT_MIN_ISOTOPE_ABUNDANCE,
        instrument_functions=instrument_functions,
        polarity=polarity,
    )
    if match_isotope_df.empty:
        runtime.logger.warning(
            f"No match isotopes found for sample '{sample_item_name}'"
        )

    # Send progress user notificaton after computing match isotopes
    if notification:
        await send_progress_user_notification(notification, 0.75)

    # Step 4: Save to the database computed match interferences and isotopes if any were found
    if not match_interference_df.empty:
        match_interference_df["sample_item_id"] = sample_item_id
        # Convert the DataFrame to a list of Pydantic models
        match_interferences = [
            MatchInterferenceBase(**row)
            for row in match_interference_df.to_dict(orient="records")
        ]
        await create_match_interferences(match_interferences)

    if not match_isotope_df.empty:
        match_isotope_df["sample_item_id"] = sample_item_id
        # Convert the DataFrame to a list of Pydantic models
        match_isotopes = [
            MatchIsotopeBase(**row)
            for row in match_isotope_df.to_dict(orient="records")
        ]
        await create_match_isotopes(match_isotopes)

    # Send progress user notificaton indicating completion of compute_and_create_sample_match_isotope_data process
    if notification:
        await send_progress_user_notification(notification, 0.95)

    return {
        "match_isotopes": match_isotope_df,
        "match_interferences": match_interference_df,
    }
