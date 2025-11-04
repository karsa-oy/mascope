import pandas as pd
from mascope_match import (
    compute_match_isotopes,
)
from mascope_backend.db.models import Sample
from mascope_backend.api.lib.api_features import (
    api_controller,
)
from mascope_backend.api.controllers.match.isotopes.match_isotopes_controller import (
    create_match_isotopes,
)

from mascope_backend.api.models.match.isotopes.match_isotopes_pydantic_model import (
    MatchIsotopeBase,
)
from mascope_backend.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)
from mascope_backend.runtime import runtime


@api_controller()
async def compute_and_create_sample_match_isotope_data(
    sample: Sample,
    target_isotopes_df: pd.DataFrame,
    notification: UserNotification | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Computes match isotopes for a given sample against a set of target isotopes.

    It updates the computation progress if progress properties are provided. Match isotopes are then saved to the database.

    :param sample: Sample model object
    :type sample: Sample
    :param target_isotopes_df: A DataFrame containing target isotope information for match computation.
    :type target_isotopes_df: DataFrame
    :param notification: Optional notification for sending progress user notifications of match computation.
    :type notification: UserNotification | None
    :return: Dictionary containing match_isotopes DataFrames
    :rtype: dict[str, pd.DataFrame]
    """
    #  Sent progress user notification if notification is provided
    if notification:
        await send_progress_user_notification(notification, 0.33)

    # Compute match isotopes for the given sample and target isotopes
    runtime.logger.info(f"Computing match isotopes for file: {sample.filename}")

    match_isotope_df = await compute_match_isotopes(
        filename=sample.filename,
        target_isotopes_df=target_isotopes_df,
        polarity=sample.polarity,
    )
    if match_isotope_df.empty:
        runtime.logger.warning(
            f"No match isotopes found for sample '{sample.sample_item_name}'"
        )

    # Send progress user notification after computing match isotopes
    if notification:
        await send_progress_user_notification(notification, 0.66)

    if not match_isotope_df.empty:
        match_isotope_df["sample_item_id"] = sample.sample_item_id
        # Convert the DataFrame to a list of Pydantic models
        match_isotopes = [
            MatchIsotopeBase(**row)
            for row in match_isotope_df.to_dict(orient="records")
        ]
        await create_match_isotopes(match_isotopes)

    # Send progress user notification indicating completion of compute_and_create_sample_match_isotope_data process
    if notification:
        await send_progress_user_notification(notification, 0.95)

    return {
        "match_isotopes": match_isotope_df,
    }
