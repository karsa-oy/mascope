import pandas as pd
import pytest
from sqlalchemy import select
from mascope_backend.db import Sample
from mascope_backend.db import async_session
import mascope_file.name as m_name
import warnings


class FakeNotification:
    def __init__(self):
        self.data = {}
        self.type = "test"


def _to_dict(sample: Sample) -> dict:
    """
    Convert Sample object to a dictionary of column names and values.
    """
    return {col.name: getattr(sample, col.name) for col in sample.__table__.columns}


@pytest.mark.asyncio
async def collect_samples():
    async with async_session() as session:
        result = await session.execute(select(Sample))
        samples = result.scalars().all()

    samples = [_to_dict(sample) for sample in samples]
    samples = pd.DataFrame(samples)

    samples["file_type"] = samples["filename"].apply(
        lambda filename: m_name.get_sample_file_type(filename)
    )
    return samples


@pytest.mark.asyncio
async def get_orbi_raw_files_collection(samples: pd.DataFrame):
    samples = samples.copy()
    samples = samples[samples["instrument"].str.lower().str.contains("orbi")]

    if samples.empty:
        warnings.warn("No Orbitrap samples found in the database!")
        return {}

    positive = samples.query("polarity == '+'")
    negative = samples.query("polarity == '-'")
    mixed = samples.query("polarity == '+-'")

    sample_files_collection = {
        "short": samples.loc[samples["length"].idxmin()],
        "long": samples.loc[samples["length"].idxmax()],
    }
    if not positive.empty:
        sample_files_collection["positive"] = positive.iloc[0]
    else:
        warnings.warn("No positive polarity Orbitrap samples found in the database!")
    if not negative.empty:
        sample_files_collection["negative"] = negative.iloc[0]
    else:
        warnings.warn("No negative polarity Orbitrap samples found in the database!")
    if not mixed.empty:
        sample_files_collection["mixed"] = mixed.iloc[0]
    else:
        warnings.warn("No mixed polarity Orbitrap samples found in the database!")
    return sample_files_collection
