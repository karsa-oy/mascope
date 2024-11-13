from sqlalchemy import (
    select,
    asc,
    desc,
    func,
)
from mascope_server.db.id import gen_id
from mascope_server.db import async_session
from mascope_server.db.models import SampleFile, InstrumentFunction
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_server.api.models.instrument_functions.instrument_function_pydantic_model import (
    InstrumentFunctionCreateBody,
    InstrumentFunctionBase,
    PeakShape,
    InstrumentFunctionFitParams,
)
from mascope_lib.instrument_functions import fit_instrument_functions
from mascope_lib.file_func import get_instrument_type
from mascope_server.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)


@api_controller()
async def get_instrument_functions(
    instrument: str = None,
    method_file: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a paginated list of instrument functions, optionally filtered by instrument and sorted by a specified column.

    Steps:
    1. Construct a query to select all instrument functions.
    2. Apply filtering if an instrument is specified.
    3. Apply sorting based on the provided sort and order parameters.
    4. Apply pagination based on the provided page and limit parameters.
    5. Execute the query and fetch the results.
    6. Convert the results into a list of dictionaries for JSON serialization.

    :param instrument: Filter by instrument name.
    :param method_file: Filter by method file name.
    :param sort: Column name to sort by.
    :param order: Sorting order ('asc' for ascending, 'desc' for descending).
    :param page: Page number for pagination.
    :param limit: Number of items per page.
    :return: A dictionary containing total results count and a list of instrument functions.
    """
    async with async_session() as session:
        stmt = select(InstrumentFunction)

        # Step 2: Apply filter if specified
        if instrument:
            stmt = stmt.filter(InstrumentFunction.instrument == instrument)
        if method_file:
            stmt = stmt.filter(InstrumentFunction.method_file == method_file)

        # Step 3: Apply sorting
        if sort:
            stmt = (
                stmt.order_by(desc(getattr(InstrumentFunction, sort)))
                if order == "desc"
                else stmt.order_by(asc(getattr(InstrumentFunction, sort)))
            )

        # Step 4: Apply pagination
        total = await session.scalar(
            select(func.count()).select_from(stmt)  # pylint: disable=not-callable
        )
        stmt = stmt.offset(page * limit).limit(limit)

        # Step 5: Execute the query
        result = await session.execute(stmt)
        instrument_functions = result.scalars().all()

        # Step 6: Convert results to dictionary
        return {
            "results": total,
            "data": [
                instrument_function.to_dict()
                for instrument_function in instrument_functions
            ],
        }


@api_controller()
async def get_method_files(filename: str):
    """
    Retrieves valid method files for a file by its filename, filtering by
    both instrument and datetime utc.

    :param filename: The filename for which to retrieve method files
    :return: A list of method file names
    """
    sample_file = await fetch_sample_file(filename)
    async with async_session() as session:
        method_files = [
            i[0]
            for i in (
                await session.execute(
                    select(InstrumentFunction.method_file)
                    .where(
                        InstrumentFunction.instrument == sample_file.instrument,
                        InstrumentFunction.datetime_utc <= sample_file.datetime_utc,
                    )
                    .distinct()
                )
            )
        ]
        return {"data": method_files}


@api_controller()
async def get_instrument_function(
    filename: str = None, instrument_function_id: str = None
) -> dict:
    """
    Retrieves a single instrument function either by the filename of a sample file or by its unique instrument function ID.

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
            stmt = select(SampleFile).filter(SampleFile.filename == filename)
            results = await session.execute(stmt)
            sample_file = results.scalars().first()
            if not sample_file:
                raise NotFoundException(
                    f"Sample file with filename {filename} not found"
                )

            stmt = (
                (
                    select(InstrumentFunction)
                    .filter(
                        InstrumentFunction.method_file == sample_file.method_file,
                        InstrumentFunction.instrument == sample_file.instrument,
                        InstrumentFunction.datetime_utc <= sample_file.datetime_utc,
                    )
                    .order_by(desc(InstrumentFunction.datetime_utc))
                )
                if sample_file.method_file
                else (
                    select(InstrumentFunction)
                    .filter(
                        InstrumentFunction.instrument == sample_file.instrument,
                        InstrumentFunction.datetime_utc <= sample_file.datetime_utc,
                    )
                    .order_by(desc(InstrumentFunction.datetime_utc))
                )
            )
        elif instrument_function_id:
            # 2B: Fetch instrument function by ID
            stmt = select(InstrumentFunction).filter(
                InstrumentFunction.instrument_function_id == instrument_function_id
            )

        # Step 3: Execute query
        results = await session.execute(stmt)
        instrument_function = results.scalars().first()

        # Step 4: Check existence
        if not instrument_function:
            detail_message = f"Instrument function {'for filename ' + filename if filename else 'with ID ' + instrument_function_id} not found"
            raise NotFoundException(detail_message)

        # Step 5: Return details
        return instrument_function.to_dict()


@api_controller()
async def create_instrument_function(
    instrument_function_data: InstrumentFunctionCreateBody,
) -> dict:
    """
    Creates a new instrument function with the provided details.

    Steps:
    1. Construct a new InstrumentFunction object with the provided details and a generated unique ID.
    2. Add the new instrument function to the session and commit the changes to the database.
    3. Refresh the instance and return the details of the created instrument function as a dictionary.

    :param instrument_function_data: Data for creating the instrument function.
    :type instrument_function_data: InstrumentFunctionCreateBody
    :return: A dictionary containing the created instrument function data.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct new instrument function
        new_instrument_function = InstrumentFunction(
            instrument_function_id=gen_id(32),
            **instrument_function_data.model_dump(),  # Unpack the Pydantic model's data
        )

        # Step 2: Add to session and commit the changes to the database
        session.add(new_instrument_function)
        await session.commit()

        # Step 3: Refresh the instance and return created instrument function
        await session.refresh(new_instrument_function)
        return {"data": new_instrument_function.to_dict()}


@api_controller()
async def delete_instrument_function(instrument_function_id: str):
    """
    Deletes a instrument function by its unique identifier.

    Steps:
    1. Fetch the instrument function by its ID from the database.
    2. If the instrument function is found, delete it from the session and commit the changes to the database.

    :param instrument_function_id: The unique identifier of the instrument function to delete.
    :type instrument_function_id: str
    :raises NotFoundException: If no instrument function is found with the provided ID.
    """
    # Step 1: Fetch the instrument function
    async with async_session() as session:
        instrument_function = await session.get(
            InstrumentFunction, instrument_function_id
        )
        if not instrument_function:
            raise NotFoundException(
                f"Instrument function with ID '{instrument_function_id}' not found"
            )

        # Step 2: Delete the instrument function and commit changes
        await session.delete(instrument_function)
        await session.commit()


@api_controller()
async def instrument_functions_fit(
    sample_file: SampleFile,
    params: InstrumentFunctionFitParams = InstrumentFunctionFitParams(),
) -> dict:
    """Fit instrument functions for the sample file.

    Steps:
    1. Fit instrument functions using the filename in the provided sample file and threshold.
    2. Convert the peak shape data from numpy arrays to lists for serialization.
    3. Extract resolution function coefficients based on the instrument type.
    4. Create an InstrumentFunctionCreateBody object with the instrument type,
    datetime, peak shape, and resolution function.
    5. Return the instrument function data along with fitting statistics.

    :param sample_file: The sample file containing spectrum for fitting instrument functions.
    :type sample_file: SampleFile
    :param params: Instrument function fitting parameters.
    :type params: InstrumentFunctionFitParams
    :return: A dict containing the fitted instrument function data and statistics.
    :rtype: dict
    """
    instrument_type = get_instrument_type(sample_file.filename)

    peakshape_numpy, resolution_function_partial, stats = (
        await fit_instrument_functions(
            sample_file.filename, r_sq_thres=params.threshold
        )
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

    instrument_function_data = InstrumentFunctionBase(
        instrument=sample_file.instrument,
        datetime_utc=sample_file.datetime_utc,
        peakshape=peakshape,
        resolution_function=resolution_function,
    )

    return {
        "data": {
            "instrument_functions": instrument_function_data,
            "statistics": stats,
        }
    }
