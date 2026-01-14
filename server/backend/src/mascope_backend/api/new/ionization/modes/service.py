from sqlalchemy import select, and_, or_

from mascope_backend.socket.records.service import (
    emit_record_created,
    emit_record_updated,
    emit_record_deleted,
)
from mascope_backend.db import async_session
from mascope_backend.db.id import gen_id
from mascope_backend.db.models import IonizationMode, SampleBatch, SampleItem
from mascope_backend.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.api.new.ionization.modes.schema import (
    IonizationModeCreate,
    IonizationModeUpdate,
)

from .util import (
    fetch_all_ionization_modes,
    resolve_ionization_modes_by_tokens,
    token_is_unique,
)


@api_controller()
async def create_ionization_mode(
    ionization_mode_data: IonizationModeCreate,
) -> dict:
    """
    Creates a new ionization mode with the provided details.

    Steps:
    1. Check for conflicting ionization mode tokens if provided.
    2. Check for conflicting ionization mode names.
    3. Construct a new IonizationMode object with the provided details.
    4. Add the new ionization mode to the session and commit the changes to the database.
    5. Refresh the instance and return the details of the created ionization mode.

    :param ionization_mode_data: The ionization mode data to create
    :return: A dictionary containing the created ionization mode data.
    """
    async with async_session() as session:
        # Step 1: Check for token conflicts if provided
        if ionization_mode_data.ionization_mode_token:
            if not await token_is_unique(ionization_mode_data.ionization_mode_token):
                raise ValueError(
                    f"Ionization mode with similar token as '{ionization_mode_data.ionization_mode_token}' already exists"
                )

        # Step 2: Check for name conflicts
        existing_name = await session.execute(
            select(IonizationMode).where(
                IonizationMode.ionization_mode_name
                == ionization_mode_data.ionization_mode_name
            )
        )
        if existing_name.scalar_one_or_none():
            raise ValueError(
                f"Ionization mode with name '{ionization_mode_data.ionization_mode_name}' already exists"
            )

        # Step 3: Create new ionization mode instance
        new_ionization_mode = IonizationMode(
            ionization_mode_id=gen_id(16),
            **ionization_mode_data.model_dump(),
        )

        # Step 4: Add to session and commit
        session.add(new_ionization_mode)
        await session.commit()

        # Step 5: Refresh and return
        await session.refresh(new_ionization_mode)

    await emit_record_created(
        record_type="ionization_mode",
        record_id=new_ionization_mode.ionization_mode_id,
        record=new_ionization_mode.to_dict(),
    )
    return {
        "message": "Ionization mode created successfully.",
        "data": new_ionization_mode.to_dict(),
    }


@api_controller()
async def get_ionization_mode(
    ionization_mode_id: str | None = None,
    token: str | None = None,
) -> dict:
    """
    Retrieves a single ionization mode either by ID or by token. One of them must be provided, but not both.

    Steps:
    1. Validate input parameters to ensure that either an ID or token is provided, but not both.
    2. Construct a query to fetch the ionization mode based on the provided parameter.
    3. Execute the query and fetch the result.
    4. Check if the ionization mode exists. If not, raise a NotFoundException.
    5. Return the ionization mode's details as a dictionary.

    :param ionization_mode_id: Unique ID of the ionization mode to retrieve directly.
    :param token: Token of the ionization mode to retrieve.
    :return: The requested ionization mode's details.
    """
    async with async_session() as session:
        # Validate input parameters
        if ionization_mode_id and token:
            raise ValueError("Provide either ionization_mode_id or token, not both.")

        if not ionization_mode_id and not token:
            raise ValueError("Provide either ionization_mode_id or token.")

        # Construct query based on parameters
        if ionization_mode_id:
            stmt = select(IonizationMode).where(
                IonizationMode.ionization_mode_id == ionization_mode_id
            )
            label = f"with ID {ionization_mode_id}"
        else:  # token
            stmt = select(IonizationMode).where(
                IonizationMode.ionization_mode_token == token
            )
            label = f"with token '{token}'"

        # Execute query
        result = await session.execute(stmt)
        ionization_mode = result.scalar_one_or_none()

        # Check existence
        if not ionization_mode:
            raise NotFoundException(f"ionization mode {label} not found")

        # Return details
        return {
            "message": f"Ionization mode {ionization_mode.ionization_mode_name} retrieved successfully.",
            "data": ionization_mode.to_dict(),
        }


@api_controller()
async def get_ionization_modes() -> dict:
    """
    Retrieves all ionization modes

    :return: A dictionary containing total results count and a list of ionization modes.
    """
    ionization_modes = await fetch_all_ionization_modes()

    return {
        "message": "Ionization modes retrieved successfully.",
        "results": len(ionization_modes),
        "data": [mode.to_dict() for mode in ionization_modes],
    }


@api_controller()
async def get_ionization_modes_by_filename(filename: str) -> dict:
    """Retrieve ionization mode(s) by sample file filename, by searching for tokens.

    :param filename: The filename of the sample file.
    :type filename: str
    :raises NotFoundException: If no ionization modes are found for the given filename.
    :return: A dictionary containing message and retrieved ionization modes.
    :rtype: dict
    """
    sample_file = await fetch_sample_file(filename)
    ionization_modes = await resolve_ionization_modes_by_tokens(sample_file)
    if not ionization_modes:
        raise NotFoundException(
            f"No ionization modes could be resolved for file '{filename}'. No valid tokens in the filename."
        )
    return {
        "message": f"Ionization modes for file {filename} retrieved successfully.",
        "data": [im.to_dict() for im in ionization_modes],
    }


@api_controller()
async def update_ionization_mode(
    ionization_mode_id: str,
    ionization_mode_data: IonizationModeUpdate,
) -> dict:
    """
    Updates an existing ionization mode.

    Steps:
    - Fetch the ionization mode by its ID from the database.
    - Check for token conflicts if token is being updated.
    - Validate calibration and diagnostic collection updates (only adding is allowed).
    - Check for name conflicts with existing acquisition batches
    - Update the fields that were provided in the request.
    - Commit the changes and return the updated ionization mode.

    :param ionization_mode_id: The ID of the ionization mode to update.
    :param ionization_mode_data: The data to update.
    :return: A dictionary containing the updated ionization mode data.
    """
    async with async_session() as session:
        # Get the existing ionization mode
        stmt = select(IonizationMode).where(
            IonizationMode.ionization_mode_id == ionization_mode_id
        )
        result = await session.execute(stmt)
        ionization_mode = result.scalar_one_or_none()

        if not ionization_mode:
            raise NotFoundException(
                f"Ionization mode with ID {ionization_mode_id} not found"
            )
        update_data = ionization_mode_data.model_dump(exclude_unset=True)
        # Check for token conflicts if being updated
        new_token = update_data.get("ionization_mode_token")
        if new_token and new_token != ionization_mode.ionization_mode_token:
            if not await token_is_unique(new_token, ignore_id=ionization_mode_id):
                raise ValueError(
                    f"Ionization mode with similar token as '{new_token}'"
                    " already exists"
                )

        # Check for calibration and diagnostic collection updates
        # Only allow adding if not yet defined, don't allow removal or changing
        if (
            "calibration_collection_id" in update_data
            and update_data["calibration_collection_id"] is not None
            and ionization_mode.calibration_collection_id
            and update_data["calibration_collection_id"]
            != ionization_mode.calibration_collection_id
        ):
            raise ValueError(
                "Cannot update calibration collection, as it is already defined"
            )
        if update_data.get("calibration_collection_id") is None:
            update_data.pop("calibration_collection_id", None)
        if (
            "diagnostic_collection_id" in update_data
            and update_data["diagnostic_collection_id"] is not None
            and ionization_mode.diagnostic_collection_id
            and update_data["diagnostic_collection_id"]
            != ionization_mode.diagnostic_collection_id
        ):
            raise ValueError(
                "Cannot update diagnostic collection, as it is already defined"
            )
        if update_data.get("diagnostic_collection_id") is None:
            update_data.pop("diagnostic_collection_id", None)

        # Check affected acquisition batches. If there are acquisition batches for this
        # ionization mode, only allow updating the token (to release it)
        affected_batches = await session.execute(
            select(SampleBatch).where(
                and_(
                    SampleBatch.sample_batch_type == "ACQUISITION",
                    or_(
                        SampleBatch.sample_batch_name.contains(
                            f"{ionization_mode.ionization_mode_name} acquisition"
                        ),
                        SampleBatch.sample_batch_name.contains(
                            f"{update_data.get('ionization_mode_name')} acquisition"
                        ),
                    ),
                )
            )
        )
        if affected_batches.scalars().first():
            # If there are affected samples, only allow updating the token (to release it)
            for key, value in update_data.items():
                match key:
                    case "ionization_mode_token":
                        # Token can always be updated
                        continue
                    case "diagnostic_collection_id" | "calibration_collection_id":
                        # Allow setting calibration and diagnostic collection if not yet defined
                        # NOTE: This does not affect existing acquisition batches
                        continue
                    case _:
                        # Other fields cannot be changed if the mode is used in acquisition batches
                        if getattr(ionization_mode, key) != value:
                            raise ValueError(
                                f"Cannot update ionization mode '{ionization_mode.ionization_mode_name}', "
                                f"as it is in use for one or more acquisition batches."
                            )

        # Update the fields that were provided
        for field, value in update_data.items():
            setattr(ionization_mode, field, value)

        # Commit and return
        await session.commit()
        await session.refresh(ionization_mode)

    await emit_record_updated(
        record_type="ionization_mode",
        record_id=ionization_mode_id,
        record=ionization_mode.to_dict(),
    )
    return {
        "message": f"Ionization mode {ionization_mode.ionization_mode_name} "
        "updated successfully.",
        "data": ionization_mode.to_dict(),
    }


@api_controller()
async def delete_ionization_mode(ionization_mode_id: str) -> dict:
    """
    Deletes an ionization mode by its unique identifier.

    Steps:
    1. Fetch the ionization mode by its ID from the database.
    2. Check if the ionization mode is associated with any samples. If so, raise an exception.
    3. If the ionization mode is found, delete it from the session and commit the changes.

    :param ionization_mode_id: The unique identifier of the ionization mode to delete.
    :return: A dictionary with a success message.
    """
    async with async_session() as session:
        # Step 1: Fetch the ionization mode
        ionization_mode = await session.get(IonizationMode, ionization_mode_id)

        if not ionization_mode:
            raise NotFoundException(
                f"Ionization mode with ID '{ionization_mode_id}' not found"
            )

        # Step 2: Check for associations with samples
        result = await session.execute(
            select(SampleItem).where(
                SampleItem.ionization_mode_id == ionization_mode_id
            )
        )
        if result.scalars().first():
            raise ValueError(
                f"Ionization mode '{ionization_mode.ionization_mode_name}' is associated with "
                "existing samples and cannot be deleted"
            )

        # Step 3: Delete the ionization mode and commit changes
        await session.delete(ionization_mode)
        await session.commit()

    await emit_record_deleted(
        record_type="ionization_mode",
        record_id=ionization_mode_id,
    )
    return {
        "message": f"Ionization mode {ionization_mode.ionization_mode_name} deleted successfully.",
    }
