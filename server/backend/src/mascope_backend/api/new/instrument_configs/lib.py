import numpy as np

from sqlalchemy import (
    select,
    desc,
)

from mascope_signal.instrument_func.fit import r_orbi
from mascope_backend.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)
from mascope_backend.db import async_session
from mascope_backend.db.models import InstrumentFunction as InstrumentConfig


async def fetch_instrument_config_by_filename(filename: str) -> InstrumentConfig | None:
    """Fetch instrument config from the database based on the sample file name.

    :param filename: Name of the sample file for which instrument functions are required.
    :type filename: str
    :return:
    :rtype: tuple(dict, function)
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
    """
    peakshape = instrument_config.peakshape
    R_p = instrument_config.resolution_function
    if len(R_p) == 1:
        # Use native Orbitrap resolution function
        p1 = R_p[0]

        def R(m):
            return r_orbi(m, p1)

    elif len(R_p) == 2:
        # Use resolution function from Junninen's thesis for TOF
        p1, p2 = R_p

        def R(m):
            return m / (p1 * m + p2)

    elif len(R_p) == 3:
        # Use 2nd order polynomial (backwards compatibility for Orbitrap) TODO: legacy
        R = np.poly1d(R_p)

    return peakshape, R


async def read_instrument_functions(filename: str) -> tuple[dict, callable]:
    """Read instrument functions from the database and parse them into
    peak shape dictionary and resolution function callable.

    :param filename: Sample file name
    :type filename: str
    :return: A tuple containing peak shape details as a dictionary and a resolution function R as a callable.
             The peak shape details include parameters defining the shape of peaks in the mass spectrum.
             The resolution function R takes a mass (m) and returns the resolution at that mass.
    :rtype: tuple[dict, callable]
    """
    instrument_config = await fetch_instrument_config_by_filename(filename)
    if instrument_config is None:
        raise ValueError(f"Instrument configuration not found for {filename}.")
    peakshape, R = parse_instrument_functions(instrument_config)
    return peakshape, R
