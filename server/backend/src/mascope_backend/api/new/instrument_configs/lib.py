from functools import partial

import numpy as np
from sqlalchemy import (
    desc,
    select,
)

from mascope_backend.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)
from mascope_backend.db import InstrumentFunction as InstrumentConfig
from mascope_backend.db import async_session
from mascope_signal.instrument_func.fit import r_orbi, r_tof


async def fetch_instrument_config_by_filename(filename: str) -> InstrumentConfig | None:
    """Fetch instrument config from the database based on the sample file name.

    :param filename: Name of the sample file for which instrument functions are required.
    :type filename: str
    :return: InstrumentConfig object containing instrument functions, or None if not found.
    :rtype: InstrumentConfig | None
    """
    async with async_session() as session:
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
        results = await session.execute(stmt)
        instrument_config = results.scalar_one_or_none()
    return instrument_config


def parse_instrument_functions(
    instrument_config: InstrumentConfig,
) -> tuple[dict, callable]:
    """Parse instrument functions read from the database, into peak shape and resolution function.

    :param instrument_config: Instrument configuration object containing peak shape and resolution function details.
    :type instrument_config: InstrumentConfig
    :return: A tuple containing peak shape details as a dictionary and a resolution function R as a callable.
             The peak shape details include parameters defining the shape of peaks in the mass spectrum.
             The resolution function R takes a mass (m) and returns the resolution at that mass.
    :rtype: tuple[dict, callable]
    :raises ValueError: If the instrument configuration does not contain the expected attributes or if they are not
                        in the expected format.
    """
    peakshape = instrument_config.peakshape
    resolution_func_coeffs = instrument_config.resolution_function

    # Validate instrument configuration
    if not (
        hasattr(instrument_config, "peakshape")
        and hasattr(instrument_config, "resolution_function")
    ):
        raise ValueError(
            (
                "Instrument config does not contain peak shape or resolution function: ",
                f"{instrument_config}.",
            )
        )
    if not (isinstance(peakshape, dict) and isinstance(resolution_func_coeffs, list)):
        raise ValueError(
            (
                "Instrument configurations are not in the expected format: ",
                f"peakshape: {peakshape}, resolution_function: {resolution_func_coeffs}.",
            )
        )

    # Derive callable from resolution function parameters
    if len(resolution_func_coeffs) == 1:
        # Use native Orbitrap resolution function
        p1 = resolution_func_coeffs[0]
        resolution_function = partial(r_orbi, a=p1)
    elif len(resolution_func_coeffs) == 2:
        # Use resolution function from Junninen's thesis for TOF
        p1, p2 = resolution_func_coeffs
        resolution_function = partial(r_tof, a=p1, b=p2)
    elif len(resolution_func_coeffs) == 3:
        # Use 2nd order polynomial (backwards compatibility for Orbitrap) TODO: legacy
        resolution_function = np.poly1d(resolution_func_coeffs)

    return peakshape, resolution_function


async def read_instrument_functions(filename: str) -> tuple[dict, callable]:
    """Read instrument functions from the database and parse them into
    peak shape dictionary and resolution function callable.

    :param filename: Sample file name
    :type filename: str
    :return: A tuple containing peak shape details as a dictionary and a resolution function R as a callable.
             The peak shape details include parameters defining the shape of peaks in the mass spectrum.
             The resolution function R takes a mass (m) and returns the resolution at that mass.
    :rtype: tuple[dict, callable]
    :raises ValueError: If no instrument configuration is found for the given filename.
    """
    instrument_config = await fetch_instrument_config_by_filename(filename)
    if instrument_config is None:
        raise ValueError(f"Instrument configuration not found for {filename}.")
    peakshape, resolution_function = parse_instrument_functions(instrument_config)
    return peakshape, resolution_function
