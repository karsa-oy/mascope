import asyncio
from sqlalchemy import (
    select,
    asc,
    desc,
    func,
)
from mascope_signal.instrument_func.fit import fit_instrument_functions
from mascope_file.name import get_instrument_type
from mascope_backend.db.id import gen_id
from mascope_backend.db import async_session
from mascope_backend.db.models import SampleFile, InstrumentFunction as InstrumentConfig
from mascope_backend.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)
from mascope_backend.api.new.instrument_configs.schemas import (
    CreateInstrumentConfigBody,
    InstrumentFunctionData,
    PeakShape,
    InstrumentConfigFitParams,
)

# This service reinforces the a uniqueness constraint:
#    "Each instrument config must have a unique
#     name (=method_file) for each instrument."
#
# This is achieved by:
#   1. Ensuring ready functions only get the most recent
#      record when duplicates are found.
#   2. Raising an exception when trying to write
#      duplicate records.
#
# TODO - refactor to move this constraint to the database


@api_controller()
async def get_instrument_configs(
    filename: str | None = None,
    instrument: str | None = None,
    method_file: str | None = None,
    datetime_utc: str | None = None,
    sort: str | None = None,
    order: str | None = None,
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a paginated list of instrument configs, optionally filtered by instrument and sorted by a specified column.

    Steps:
    1. Construct select query.
    2. Apply filtering if specified.
    3. Group by method_file and instrument to enforce uniqueness
    3. Apply sorting if specified
    4. Apply pagination based on page/limit args
    5. Execute the query and fetch the results
    6. Serialize results for the API

    :param instrument: Filter by instrument name.
    :param config_name: Filter by config name.
    :param datetime_utc: Filter by datetime utc
    :param sort: Column name to sort by.
    :param order: Sorting order ('asc' for ascending, 'desc' for descending).
    :param page: Page number for pagination.
    :param limit: Number of items per page.
    :return: A dictionary containing total results count and a list of instrument functions.
    """
    async with async_session() as session:
        # Step 1: construct query
        stmt = select(InstrumentConfig)

        if filename and (instrument or method_file):
            raise ValueError(
                "get instrument configs: when providing a filename, you may not provide an instrument or method_file"
            )

        # Step 2: Apply filters if provided
        if instrument:
            stmt = stmt.where(InstrumentConfig.instrument == instrument)
        if method_file:
            stmt = stmt.where(InstrumentConfig.method_file == method_file)
        if filename:
            sample_file = await fetch_sample_file(filename)
            stmt = stmt.where(
                InstrumentConfig.instrument == sample_file.instrument,
            )
        if datetime_utc:
            stmt = stmt.where(InstrumentConfig.datetime_utc == datetime_utc)

        # Step 3: Group by method_file & instrument to enforce uniqueness
        stmt = stmt.group_by(
            InstrumentConfig.method_file, InstrumentConfig.instrument
        ).having(func.max(InstrumentConfig.datetime_utc))

        # Step 4: Apply sorting
        if sort:
            stmt = (
                stmt.order_by(desc(getattr(InstrumentConfig, sort)))
                if order == "desc"
                else stmt.order_by(asc(getattr(InstrumentConfig, sort)))
            )

        # Step 4: Apply pagination
        total = await session.scalar(
            select(func.count()).select_from(stmt)  # pylint: disable=not-callable
        )
        stmt = stmt.offset(page * limit).limit(limit)

        # Step 5: Execute the query
        result = await session.execute(stmt)
        instrument_configs = result.scalars().all()

        # Step 6: Serialize results to dict
        return {
            "message": "Instrument functions retrieved successfully.",
            "results": total,
            "data": [config.to_dict() for config in instrument_configs],
        }


@api_controller()
async def get_instrument_config(
    filename: str | None = None,
    instrument_function_id: str | None = None,
) -> dict:
    """
    Retrieves a single instrument config either by the filename of a sample file or by its unique instrument function ID.

    Steps:
    1. Validate input parameters to ensure that either a filename or an instrument_function_id is provided, but not both.
    2A. If a filename is provided, construct a query to fetch the latest valid instrument function, filtering by method file is the sample file has one set.
    2B. If an instrument_function_id is provided, construct a query to fetch the instrument function directly by its ID.
    3. Execute the query and fetch the result.
    4. Check if the instrument function exists. If not, raise a NotFoundException with an appropriate message based on the provided parameters.
    5. Return the instrument function's details as a dictionary, including relevant fields such as resolution, peak shape parameters, etc.

    :param filename: Filename to query for the latest instrument function, based on the file's creation date and time.
    :type filename: str, optional
    :param instrument_function_id: Unique ID of the instrument function to retrieve directly.
    :type instrument_function_id: str, optional
    :raises ValueError: If both a filename and an instrument_function_id are provided, indicating an ambiguous request.
    :raises NotFoundException: If no sample file with the provided filename is found in the database.
    :raises NotFoundException: If no instrument function is found based on the given filename or instrument_function_id.
    :return: The requested instrument function's details, including parameters like resolution and peak shape.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Validate input parameters
        if filename and instrument_function_id:
            raise ValueError(
                "Provide either filename or instrument_function_id, not both."
            )

        # Step 2: Construct query based on parameters
        if filename:
            # 2A: Fetch instrument function by filename
            sample_file = await fetch_sample_file(filename=filename)
            stmt = (
                (
                    select(InstrumentConfig)
                    .where(
                        InstrumentConfig.method_file == sample_file.method_file,
                        InstrumentConfig.instrument == sample_file.instrument,
                    )
                    .order_by(desc(InstrumentConfig.datetime_utc))
                    .limit(1)
                )
                if sample_file.method_file
                else (
                    select(InstrumentConfig)
                    .where(
                        InstrumentConfig.instrument == sample_file.instrument,
                    )
                    .order_by(desc(InstrumentConfig.datetime_utc))
                    .limit(1)
                )
            )
        elif instrument_function_id:
            # 2B: Fetch instrument function by ID
            stmt = select(InstrumentConfig).where(
                InstrumentConfig.instrument_function_id == instrument_function_id
            )

        # Step 3: Execute query
        results = await session.execute(stmt)
        instrument_config = results.scalar_one_or_none()

        # Step 4: Check existence
        if not instrument_config:
            if filename:
                label = f"for filename {filename}"
            elif instrument_function_id:
                label = f"with ID {instrument_function_id}"
            raise NotFoundException(f"Instrument config {label} not found")

        # Step 5: Return details
        return {
            "message": "Instrument config retrieved successfully.",
            "data": instrument_config.to_dict(),
        }


@api_controller()
async def create_instrument_config(
    instrument_config: CreateInstrumentConfigBody,
) -> dict:
    """
    Creates a new instrument function with the provided details.

    Steps:
    1. Check for conflicting instrument configs
    2. Construct a new InstrumentConfig object with the provided details and a generated unique ID.
    3. Add the new instrument function to the session and commit the changes to the database.
    4. Refresh the instance and return the details of the created instrument function as a dictionary.

    :param config: Data for creating the instrument function.
    :type config: InstrumentConfigCreateBody
    :return: A dictionary containing the created instrument function data.
    :rtype: dict
    """
    # Step 1: Check for conflicting instrument configs
    conflicts = (
        await get_instrument_configs(
            instrument=instrument_config.instrument,
            method_file=instrument_config.method_file,
        )
    )["data"]
    if conflicts:
        raise ValueError(
            f"An instrument config with method_file {instrument_config.method_file} already exists for instrument {instrument_config.instrument}"
        )

    async with async_session() as session:
        # Step 2: Construct new instrument function
        new_instrument_config = InstrumentConfig(
            instrument_function_id=gen_id(32),
            **instrument_config.model_dump(),  # Unpack the Pydantic model's data
        )

        # Step 3: Add to session and commit the changes to the database
        session.add(new_instrument_config)
        await session.commit()

        # Step 4: Refresh the instance and return created instrument function
        await session.refresh(new_instrument_config)
        return {
            "message": "Instrument config created successfully.",
            "data": new_instrument_config.to_dict(),
        }


@api_controller()
async def delete_instrument_config(instrument_function_id: str):
    """
    Deletes a instrument function by its unique identifier.

    Steps:
    1. Fetch the instrument function by its ID from the database.
    2. If the instrument function is found, delete it from the session and commit the changes to the database.

    :param instrument_function_id: The unique identifier of the instrument function to delete.
    :type instrument_function_id: str
    :raises NotFoundException: If no instrument function is found with the provided ID.
    """
    # Step 1. Get full record from the ID
    instrument_config = (
        await get_instrument_config(instrument_function_id=instrument_function_id)
    ).get("data")

    # Step 2. Retrieve all instrument configs with the same instrument and method file
    async with async_session() as session:
        result = await session.execute(
            select(InstrumentConfig).where(
                InstrumentConfig.instrument == instrument_config["instrument"],
                InstrumentConfig.method_file == instrument_config["method_file"],
            )
        )
        instrument_configs = result.scalars().all()
    # Step 3. Gather all IDs to be deleted
    instrument_function_ids = [
        conf.instrument_function_id for conf in instrument_configs
    ]

    # Step 4: Delete records
    async def delete_record(id):
        async with async_session() as session:
            instrument_config = await session.get(InstrumentConfig, id)
            if not instrument_config:
                raise NotFoundException(
                    f"Instrument config with ID '{instrument_function_id}' not found"
                )

            # Step 2: Delete the instrument function and commit changes
            await session.delete(instrument_config)
            await session.commit()

    delete_tasks = [delete_record(id) for id in instrument_function_ids]
    await asyncio.gather(*delete_tasks)

    return {
        "message": "Instrument function deleted successfully.",
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
)
async def fit_instrument_config(
    sample_file: SampleFile,
    fit_params: InstrumentConfigFitParams = InstrumentConfigFitParams(),
    independent_transaction: bool = False,
    sid=None,
    process_id=None,
    parent_id=None,
) -> dict:
    """Fit instrument functions for the sample file.

    Steps:
    1. Fit instrument functions using the filename in the provided sample file and threshold.
    2. Convert the peak shape data from numpy arrays to lists for serialization.
    3. Extract resolution function coefficients based on the instrument type.
    4. Create an InstrumentConfigCreateBody object with the instrument type,
    datetime, peak shape, and resolution function.
    5. Return the instrument function data along with fitting statistics.

    :param sample_file: The sample file containing spectrum for fitting instrument functions.
    :type sample_file: SampleFile
    :param params: Instrument function fitting parameters.
    :type params: InstrumentConfigFitParams
    :return: A dict containing the fitted instrument function data and statistics.
    :rtype: dict
    """
    instrument_type = get_instrument_type(sample_file.filename)
    dmz = 0.01 if instrument_type == "orbi" else 0.5

    (
        peakshape_numpy,
        resolution_function_partial,
        stats,
    ) = await fit_instrument_functions(
        sample_file.filename, r_sq_thres=fit_params.threshold, dmz=dmz
    )

    # Convert peakshape to lists to be serialized
    peakshape = PeakShape(
        x=peakshape_numpy["x"].tolist(), y=peakshape_numpy["y"].tolist()
    )

    # Get resolution function coefficients
    partial_coefficients = resolution_function_partial.keywords
    if instrument_type == "tof":
        resolution_function = [partial_coefficients["a"], partial_coefficients["b"]]
    else:
        resolution_function = [partial_coefficients["a"]]

    instrument_function_data = InstrumentFunctionData(
        instrument=sample_file.instrument,
        datetime_utc=sample_file.datetime_utc,
        peakshape=peakshape,
        resolution_function=resolution_function,
    )

    instrument_functions = instrument_function_data.model_dump()
    instrument_functions["datetime_utc"] = instrument_functions[
        "datetime_utc"
    ].isoformat()

    return {
        "message": f"Instrument functions succesfully fitted for {sample_file.filename}",
        "data": {
            "instrument_functions": instrument_function_data,
            "statistics": stats,
        },
        "_notification_data": {
            "instrument_functions": instrument_functions,
            "statistics": stats,
        },
    }
