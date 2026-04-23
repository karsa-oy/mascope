"""Datasets resource for the Mascope SDK."""

import pandas as pd
from loguru import logger

from ._base import BaseResource, _coerce_datetime_columns


class DatasetsResource(BaseResource):
    """Resource for dataset operations.

    Datasets are the top-level organizational unit in Mascope, containing
    sample batches and related data.

    Example::

        from mascope_sdk import MascopeClient

        mascope = MascopeClient()

        # List all datasets
        datasets = mascope.datasets.list()
        print(datasets[["dataset_id", "dataset_name"]])
    """

    def list(self) -> pd.DataFrame | None:
        """List all accessible datasets.

        :return: A DataFrame containing dataset information with columns
                 including ``dataset_id`` and ``dataset_name``, or None if no
                 datasets are found.
        :rtype: pd.DataFrame | None
        :raises AuthenticationError: If authentication fails.
        :raises MascopeAPIError: If the API request fails.

        Example::

            datasets = mascope.datasets.list()
            print(datasets[["dataset_id", "dataset_name"]])
        """
        cache_key = "datasets"
        if cache_key in self._client._cache:
            return self._client._cache[cache_key]
        logger.info("Fetching datasets")
        data = self._get("datasets")
        if not data:
            return None
        df = _coerce_datetime_columns(pd.DataFrame(data))
        logger.info("Found {} dataset(s)", len(df))
        self._client._cache[cache_key] = df
        return df
