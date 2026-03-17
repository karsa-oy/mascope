"""Base resource class for Mascope SDK resources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd
from loguru import logger

from .._http import http_get, http_post

if TYPE_CHECKING:
    from ..client import MascopeClient


def _coerce_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert known datetime columns to proper datetime types.

    Columns ending with a UTC suffix are converted to ``datetime64[ns, UTC]``.
    Columns matching a local datetime name are converted to ``datetime64[ns]``.
    """
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        if "datetime" in col:
            is_utc = "utc" in col
            try:
                df[col] = pd.to_datetime(df[col], utc=is_utc)
            except Exception as e:  # pylint: disable=broad-except
                logger.warning(f"Failed to convert column {col} to datetime: {e}")
    return df


class BaseResource:
    """Base class for all API resource classes.

    Provides common functionality for making API requests using the
    client's credentials.
    """

    def __init__(self, client: "MascopeClient"):
        """Initialize the resource with a client reference.

        :param client: The MascopeClient instance to use for requests.
        :type client: MascopeClient
        """
        self._client = client

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> Any:
        """Make a GET request to the API.

        :param path: API path (without /api/ prefix).
        :type path: str
        :param params: Query parameters.
        :type params: dict[str, Any], optional
        :param stream: Whether to stream the response.
        :type stream: bool, optional
        :return: Parsed JSON response data.
        :rtype: Any
        """
        response = http_get(
            url=self._client.url,
            path=path,
            access_token=self._client.access_token,
            params=params,
            stream=stream,
            verify_ssl=self._client._verify_ssl,
            service_name=self._client._service_name,
        )
        if stream:
            return response
        return response.json().get("data")

    def _post(
        self,
        path: str,
        data: dict[str, Any],
    ) -> Any:
        """Make a POST request to the API.

        :param path: API path (without /api/ prefix).
        :type path: str
        :param data: Request body data.
        :type data: dict[str, Any]
        :return: Parsed JSON response data.
        :rtype: Any
        """
        response = http_post(
            url=self._client.url,
            path=path,
            access_token=self._client.access_token,
            data=data,
            verify_ssl=self._client._verify_ssl,
            service_name=self._client._service_name,
        )
        return response.json().get("data")
