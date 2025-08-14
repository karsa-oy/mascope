"""
Ionization mechanisms validation utilities.

Provides data access and validation operations for ionization mechanisms,
including polarity compatibility validation for sample batches.
"""

from sqlalchemy import select
from mascope_backend.db import async_session
from mascope_backend.db.models import IonizationMechanism
from mascope_backend.api.models.sample.batches.config import sample_batch_config
from mascope_backend.api.lib.exceptions.api_exceptions import (
    ApiException,
    NotFoundException,
)
from mascope_backend.runtime import runtime


async def validate_ionization_mechanisms_polarity(
    ionization_mechanism_ids: list[str],
    batch_polarity: str,
    sample_batch_type: str,
) -> None:
    """
    Validates that ionization mechanisms are compatible with batch polarity.

    For mixed polarity batches (+-), all mechanisms are allowed.
    For single polarity batches (+/-), only matching mechanisms are allowed.

    :param ionization_mechanism_ids: List of ionization mechanism IDs to validate.
    :type ionization_mechanism_ids: list[str]
    :param batch_polarity: The polarity of the sample batch ('+', '-', or '+-').
    :type batch_polarity: str
    :param sample_batch_type: The type of sample batch ('ACQUISITION' or 'ANALYSIS').
    :type sample_batch_type: str
    :raises NotFoundException: If any ionization mechanisms are not found.
    :raises ApiException: If any ionization mechanisms are incompatible with batch polarity.
    """
    # Mixed polarity batches accept all mechanisms
    if batch_polarity == sample_batch_config.ANALYSIS_POLARITY:
        return

    # Fetch ionization mechanism details
    async with async_session() as session:
        stmt = select(
            IonizationMechanism.ionization_mechanism_id,
            IonizationMechanism.ionization_mechanism,
            IonizationMechanism.ionization_mechanism_polarity,
        ).where(
            IonizationMechanism.ionization_mechanism_id.in_(ionization_mechanism_ids)
        )

        result = await session.execute(stmt)
        ionization_mechanisms = result.fetchall()

    # Check for missing mechanisms
    found_mechanism_ids = {im.ionization_mechanism_id for im in ionization_mechanisms}
    if missing_ids := set(ionization_mechanism_ids) - found_mechanism_ids:
        raise NotFoundException(
            f"Ionization mechanisms not found: {', '.join(missing_ids)}"
        )

    # Check polarity compatibility
    if incompatible := [
        f"'{im.ionization_mechanism}' (polarity: {im.ionization_mechanism_polarity})"
        for im in ionization_mechanisms
        if im.ionization_mechanism_polarity != batch_polarity
    ]:
        error_message = (
            f"The ionization mechanisms {', '.join(incompatible)} are incompatible with "
            f"{sample_batch_type.lower()} batch polarity '{batch_polarity}'."
        )
        runtime.logger.error(error_message)
        raise ApiException(
            error_message,
            {
                "incompatible_mechanisms": incompatible,
                "batch_polarity": batch_polarity,
            },
            400,
        )
