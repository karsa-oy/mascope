"""Legacy API functions (deprecated).

This module contains deprecated functions that are scheduled for removal
in a future release. These functions are preserved for backwards compatibility
but new code should use :class:`MascopeClient` instead.

.. deprecated::
    All functions in this module are deprecated. Use :class:`MascopeClient` for new code.

Migration Guide:
    Old API::

        from mascope_sdk import get_workspaces, get_sample_batches
        workspaces = get_workspaces(url, token)
        batches = get_sample_batches(url, token, workspace_id)

    New API::

        from mascope_sdk import MascopeClient
        mascope = MascopeClient()  # Loads credentials from .env
        workspaces = mascope.workspaces.list()
        batches = mascope.batches.list(workspace_id)
"""

import functools
import json
import warnings

import requests
from loguru import logger
from requests.exceptions import HTTPError, RequestException, Timeout

# Default service name to use in request header. Override SERVICE_NAME for specific agents
SERVICE_NAME = "mascope_sdk"


def _get_service_name() -> str:
    """Return the current SERVICE_NAME from the package namespace.

    Agents override ``mascope_sdk.SERVICE_NAME`` at the package level,
    so we look it up dynamically rather than capturing the module-level
    default.
    """
    import sys  # pylint: disable=C0415 noqa: PLC0415 deferred to avoid import-time cost

    pkg = sys.modules.get("mascope_sdk")
    if pkg is not None:
        return getattr(pkg, "SERVICE_NAME", SERVICE_NAME)
    return SERVICE_NAME


def _deprecated(new_api_hint: str):
    """Decorator to mark functions as deprecated with migration guidance.

    :param new_api_hint: A string describing how to use the new API instead.
    :type new_api_hint: str
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated and will be removed in a future release. "
                f"Use {new_api_hint} instead. "
                "See the README for migration guidance.",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return wrapper

    return decorator


######################
# API request wrappers
# NOTE: These are internal helpers for the legacy functions.
# New code should use MascopeClient instead.


def api_get(
    url: str, path: str, access_token: str, params: dict = None, stream: bool = False
):
    """Send a GET request to the specified API endpoint with optional query parameters.

    Optionally, the response can be streamed to handle large response bodies. In streaming mode,
    the function will return the response object without attempting to parse the content, allowing
    the caller to process the response in chunks.

    .. note::
        When using streaming, the caller is responsible for closing the response.

    :param url: The base URL of the server.
    :type url: str
    :param path: The specific API path to be appended to the base URL.
    :type path: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param params: A dictionary of query parameters to include in the request.
    :type params: dict, optional
    :param stream: Whether to stream the response content, defaults to False.
    :type stream: bool, optional
    :return: The response object if the request was successful, otherwise None.
    :rtype: requests.Response or None
    """
    full_url = url + "/api/" + path
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Service-Name": _get_service_name(),
        }

        # Send GET request with query parameters (if provided)
        resp = requests.get(
            full_url,
            params=params,
            headers=headers,
            verify=False,
            timeout=(30, 300),  # (connect timeout, read timeout)
            stream=stream,
        )
        resp.raise_for_status()  # Raise HTTPError for bad responses
        # Skip message parsing for streamed responses to avoid loading entire content into memory
        if not stream:
            message = json.loads(resp.content).get("message", None)
            if message is not None:
                logger.debug(message)
    except HTTPError as http_err:
        if resp.status_code == 401 or resp.status_code == 403:
            response = json.loads(resp.content)
            error_message = response.get("detail", {}).get("error_message", None)
            logger.error(f"{error_message} Please check your API token.")
        else:
            try:
                error_message = (
                    json.loads(resp.content)
                    .get("detail", {})
                    .get(
                        "error_message",
                        "No additional error information from the server.",
                    )
                )
            except json.JSONDecodeError:
                error_message = "Failed to decode error message from server response."
            logger.error(
                f"HTTP error: Unable to retrieve data from {full_url}. \nDetails: {http_err} \nServer message: {error_message}"
            )
        return None
    except Timeout:
        logger.error(f"Timeout error: The request to {full_url} timed out.")
        return None
    except RequestException as req_err:
        logger.error(
            f"Connection error: Could not connect to {full_url}. Please check the URL and your network connection. \nDetails: {req_err}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Error: An unexpected error occurred while trying to reach {full_url}. \nDetails: {str(e)}"
        )
        return None
    return resp


def api_post(url: str, path: str, access_token: str, data: dict):
    """Send a POST request to the specified API endpoint with provided data.

    :param url: The base URL of the server.
    :type url: str
    :param path: The specific API path to be appended to the base URL.
    :type path: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param data: The data payload to send in the POST request.
    :type data: dict
    :return: The response object if the request was successful, otherwise None.
    :rtype: requests.Response or None
    """
    full_url = url + "/api/" + path
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Service-Name": _get_service_name(),
        }
        resp = requests.post(
            full_url, data=json.dumps(data), headers=headers, verify=False, timeout=30
        )
        resp.raise_for_status()  # Raise HTTPError for bad responses
        message = json.loads(resp.content).get("message", None)
        if message is not None:
            logger.debug(message)
    except HTTPError as http_err:
        if resp.status_code == 401 or resp.status_code == 403:
            response = json.loads(resp.content)
            error_message = response.get("detail", {}).get("error_message", None)
            logger.error(f"{error_message} Please check your API token.")
        else:
            try:
                error_message = (
                    json.loads(resp.content)
                    .get("detail", {})
                    .get(
                        "error_message",
                        "No additional error information from the server.",
                    )
                )
            except json.JSONDecodeError:
                error_message = "Failed to decode error message from server response."
            logger.error(
                f"HTTP error: Unable to retrieve data from {full_url}. \nDetails: {http_err} \nServer message: {error_message}"
            )
        return None
    except Timeout:
        logger.error(f"Timeout error: The request to {full_url} timed out.")
        return None
    except RequestException as req_err:
        logger.error(
            f"Connection error: Could not connect to {full_url}. Please check the URL and your network connection. \nDetails: {req_err}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Error: An unexpected error occurred while trying to reach {full_url}. \nDetails: {str(e)}"
        )
        return None
    return resp


def api_post_file(
    url: str,
    path: str,
    access_token: str,
    filepath: str,
):
    """Send a POST request to the specified API endpoint with a path file to be uploaded.

    :param url: The base URL of the server.
    :type url: str
    :param path: The specific API path to be appended to the base URL.
    :type path: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param filepath: Path to the file to be uploaded.
    :type filepath: str
    :return: The response object if the request was successful, otherwise None.
    :rtype: requests.Response or None
    """
    full_url = url + "/api/" + path
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Service-Name": _get_service_name(),
        }
        with open(filepath, "rb") as file:
            resp = requests.post(
                full_url,
                files=[("files", file)],
                headers=headers,
                verify=False,
                timeout=60,
            )
        resp.raise_for_status()  # Raise HTTPError for bad responses
        message = json.loads(resp.content).get("message", None)
        if message is not None:
            logger.debug(message)
    except HTTPError as http_err:
        if resp.status_code == 401 or resp.status_code == 403:
            response = json.loads(resp.content)
            error_message = response.get("detail", {}).get("error_message", None)
            logger.error(f"{error_message} Please check your API token.")
        else:
            try:
                error_message = (
                    json.loads(resp.content)
                    .get("detail", {})
                    .get(
                        "error_message",
                        "No additional error information from the server.",
                    )
                )
            except json.JSONDecodeError:
                error_message = "Failed to decode error message from server response."
            logger.error(
                f"HTTP error: Unable to retrieve data from {full_url}. \nDetails: {http_err} \nServer message: {error_message}"
            )
        return None
    except Timeout:
        logger.error(f"Timeout error: The request to {full_url} timed out.")
        return None
    except RequestException as req_err:
        logger.error(
            f"Connection error: Could not connect to {full_url}. Please check the URL and your network connection. \nDetails: {req_err}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Error: An unexpected error occurred while trying to reach {full_url}. \nDetails: {str(e)}"
        )
        return None
    return resp


################
# Workspaces API


@_deprecated("MascopeClient().workspaces.list()")
def get_workspaces(mascope_url: str, access_token: str) -> list:
    """Get Mascope workspaces from a URL.

    .. deprecated::
        Use :meth:`MascopeClient.workspaces.list` instead.

    :param mascope_url: Mascope URL.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :return: List of workspace dictionaries.
    :rtype: list
    """
    resp = api_get(url=mascope_url, path="workspaces", access_token=access_token)
    # Check if the request was successful
    if not resp:
        logger.error(
            f"Failed to retrieve workspaces from {mascope_url}. Please check the URL and try again."
        )
        return []

    content = json.loads(resp.content)
    workspaces = content.get("data", [])
    if not workspaces:
        logger.error("No workspaces found. Please create a new workspace.")

    return workspaces


####################
# Sample batches API


@_deprecated("MascopeClient().batches.list(workspace_id)")
def get_sample_batches(mascope_url: str, access_token: str, workspace_id: str) -> list:
    """Get Mascope sample batches of a workspace.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param workspace_id: The ID of the workspace from which to retrieve sample batches.
    :type workspace_id: str
    :return: A list of sample batch dictionaries.
             Returns an empty list if no sample batches are found or if an error occurs.
    :rtype: list
    """
    # Prepare query parameters
    query_params = {"workspace_id": workspace_id}

    # Perform the GET request with query parameters
    resp = api_get(
        url=mascope_url,
        path="sample/batches",
        access_token=access_token,
        params=query_params,
    )

    # Check if the request was successful
    if not resp:
        logger.error(
            f"Failed to retrieve sample batches from {mascope_url}. Please check the URL and try again."
        )
        return []

    content = json.loads(resp.content)
    batches = content.get("data", [])

    if not batches:
        logger.error("No sample batches found. Please create a new sample batch.")

    return batches


@_deprecated("MascopeClient().batches.get_data(batch_id)")
def get_sample_batch_data(
    mascope_url: str,
    access_token: str,
    sample_batch_id: str,
) -> dict:
    """Retrieve detailed data for all samples in a sample batch.

    This function interacts with the Mascope API to fetch comprehensive data
    for a given sample batch. It retrieves data for samples and combined match/targets data
    for compounds, ions and isotopes.

    The data is retrieved in streaming mode to be able to handle potentially large responses.

    - Call the API to get the batch data
    - Parse the streamed response content
    - Extract relevant information from the aggregate match data
    - Build the response structure containing batch information, samples and combined target/match
      data for compounds, ions, and isotopes.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_batch_id: The ID of the sample batch to retrieve data for.
    :type sample_batch_id: str
    :return: A dictionary containing:

             - ``result``: Summary statistics about the retrieved data.
             - ``sample_batch``: Information about the sample batch.
             - ``samples``: A list of samples within the batch.
             - ``compounds``: Data for compounds.
             - ``ions``: Data for ions.
             - ``isotopes``: Data for isotopes.

             Returns an empty dictionary if the request fails or no data is found.
    :rtype: dict
    """
    # - Call the API to get the batch data (stored in database)
    resp = api_get(
        url=mascope_url,
        path=f"match/targets/batch/{sample_batch_id}",
        access_token=access_token,
        stream=True,
    )
    if not resp:
        logger.error(
            f"Failed to retrieve match data for sample batch with ID {sample_batch_id}."
        )
        return {}

    # - Parse the streamed response content
    # Use iter_content to read chunks and accumulate, avoiding loading entire response at once
    try:
        chunks = []
        for chunk in resp.iter_content(chunk_size=8192, decode_unicode=True):
            if chunk:
                chunks.append(chunk)
        content = "".join(chunks)
        batch_data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse JSON response for sample batch {sample_batch_id}: {e}"
        )
        return {}
    finally:
        resp.close()  # Ensure the connection is released back to the pool

    if not batch_data:
        logger.error(f"No data returned for sample batch with ID {sample_batch_id}.")
        return {}

    # - Extract relevant information from the aggregate match data
    result = batch_data.get("result", {})
    sample_batch = batch_data.get("data", {}).get("sample_batch", {})
    samples = batch_data.get("data", {}).get("samples", [])
    compounds = batch_data.get("data", {}).get("compounds", [])
    ions = batch_data.get("data", {}).get("ions", [])
    isotopes = batch_data.get("data", {}).get("isotopes", [])

    # - Build the response structure
    response = {
        "result": result,
        "sample_batch": sample_batch,
        "samples": samples,
        "compounds": compounds,
        "ions": ions,
        "isotopes": isotopes,
    }

    return response


#############
# Samples API


@_deprecated("MascopeClient().samples.list(batch_id)")
def get_samples(mascope_url: str, access_token: str, sample_batch_id: str) -> list:
    """Get Mascope samples of the specified sample batch.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_batch_id: The ID of the sample batch from which to retrieve samples.
    :type sample_batch_id: str
    :return: A list of sample dictionaries.
             Returns an empty list if no samples are found or if an error occurs.
    :rtype: list
    """
    # Prepare query parameters
    query_params = {"sample_batch_id": sample_batch_id}

    # Perform the GET request with query parameters
    resp = api_get(
        url=mascope_url, path="samples", access_token=access_token, params=query_params
    )

    # Check if the API request was successful
    if not resp:
        logger.error(
            f"Failed to retrieve samples from {mascope_url}. Please check the URL and try again."
        )
        return []

    content = json.loads(resp.content)
    samples = content.get("data", [])
    if not samples:
        logger.error(f"No samples found for sample batch with ID {sample_batch_id}.")

    return samples


@_deprecated("MascopeClient().samples.get(sample_id)")
def get_sample(mascope_url: str, access_token: str, sample_item_id: str) -> dict:
    """Get details of a specific sample by its ID.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_item_id: The ID of the sample item to retrieve.
    :type sample_item_id: str
    :return: The response dictionary containing the sample details, or None if an error occurs.
    :rtype: dict
    """
    resp = api_get(
        url=mascope_url,
        path=f"samples/{sample_item_id}",
        access_token=access_token,
    )
    if not resp:
        logger.error(f"Failed to retrieve sample details from {mascope_url}.")
        return None

    sample = json.loads(resp.content)
    if not sample:
        logger.error(f"No sample with ID {sample_item_id} found.")
    return sample


@_deprecated("MascopeClient().matching.match_compound(sample_id, formula, name)")
def get_sample_compound_matches(
    mascope_url: str,
    access_token: str,
    sample_item_id: str,
    target_compound_formula: str,
    target_compound_name: str = "Unknown Compound",
    match_params: dict = None,
) -> dict:
    """Retrieve matches for compounds within a sample based on a target compound formula.

    Applies specified filter parameters to filter the matches.

    :param mascope_url: Base URL of the Mascope API.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_item_id: Unique identifier of the sample item to analyze.
    :type sample_item_id: str
    :param target_compound_formula: Chemical formula of the target compound.
    :type target_compound_formula: str
    :param target_compound_name: The name of the target compound, defaults to "Unknown Compound".
    :type target_compound_name: str, optional
    :param match_params: Parameters to filter the match results.
    :type match_params: dict, optional
    :return: A dictionary containing the match data (compound->ions->isotopes).
             Returns None if no match data is found or if an error occurs.
    :rtype: dict
    """
    # Construct the request body
    body = {
        "target_compound": {
            "target_compound_formula": target_compound_formula,
            "target_compound_name": target_compound_name,
        }
    }
    if match_params is not None:
        body["match_params"] = match_params

    # Make the POST request for the specified sample
    resp = api_post(
        url=mascope_url,
        path=f"match/aggregate/sample/{sample_item_id}/compound",
        access_token=access_token,
        data=body,
    )

    # Check if the API request was successful
    if not resp:
        logger.error(
            f"Failed to retrieve compound '{target_compound_formula}' match data for for sample item ID {sample_item_id} from {mascope_url}."
        )
        return None

    # Parse the content of the response
    response_json = resp.json()
    match_data = response_json.get("data", None)

    if not match_data:
        logger.error(
            f"No compound matches found for sample item ID {sample_item_id} and target compound {target_compound_formula}."
        )
        return None

    return match_data


@_deprecated("MascopeClient().matching.match_compounds(sample_id, formulas)")
def get_sample_compounds_matches(
    mascope_url: str,
    access_token: str,
    sample_item_id: str,
    target_compound_formulas: list[str],
    match_params: dict = None,
    ion_mechanism_ids: list[str] = None,
) -> dict:
    """Retrieve matches for multiple compounds within a sample.

    Based on a list of target compound formulas, applying specified filter parameters
    to filter the matches.

    :param mascope_url: Base URL of the Mascope API.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_item_id: Unique identifier of the sample item to analyze.
    :type sample_item_id: str
    :param target_compound_formulas: List of chemical formulas of the target compounds.
    :type target_compound_formulas: list[str]
    :param match_params: Parameters to filter the match results.
    :type match_params: dict, optional
    :param ion_mechanism_ids: List of ionization mechanism IDs to use in matching.
    :type ion_mechanism_ids: list[str], optional
    :return: A dictionary containing the match data (compound->ions->isotopes).
             Returns None if no match data is found or if an error occurs.
    :rtype: dict
    """
    body = {
        "target_compound_formulas": target_compound_formulas,
    }
    if match_params is not None:
        body["match_params"] = match_params
    if ion_mechanism_ids is not None:
        body["ion_mechanism_ids"] = ion_mechanism_ids

    resp = api_post(
        url=mascope_url,
        path=f"match/aggregate/sample/{sample_item_id}/compounds",
        access_token=access_token,
        data=body,
    )

    if not resp:
        logger.error(
            f"Failed to retrieve compound matches for sample item ID {sample_item_id} from {mascope_url}."
        )
        return None

    response_json = resp.json()
    match_data = response_json.get("data", None)

    if not match_data:
        logger.error(
            f"No compound matches found for sample item ID {sample_item_id} and target compounds {target_compound_formulas}."
        )
        return None

    return match_data


@_deprecated("MascopeClient().samples.get_peaks(sample_id)")
def get_sample_peaks(
    mascope_url: str,
    access_token: str,
    sample_item_id: str,
    areas: bool = True,
    heights: bool = True,
    average: bool = True,
    matches: bool = False,
    t_min: float | None = None,
    t_max: float | None = None,
    mz_min: float | None = None,
    mz_max: float | None = None,
) -> dict | None:
    """Get peak data from a sample with automatic polarity filtering and optional range filtering.

    This function uses the sample-based endpoint that provides sample polarity filtering,
    time limits controls, and m/z range filtering based on the sample's acquisition parameters.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_item_id: The ID of the sample item from which to retrieve peak data.
    :type sample_item_id: str
    :param areas: Include peak areas in the response. Defaults to True.
    :type areas: bool, optional
    :param heights: Include peak heights in the response. Defaults to True.
    :type heights: bool, optional
    :param average: If True, return averaged peak data. Defaults to True.
    :type average: bool, optional
    :param matches: If True, include matched compounds/ions/isotopes. Defaults to False.
    :type matches: bool, optional
    :param t_min: Minimum time limit in seconds.
    :type t_min: float, optional
    :param t_max: Maximum time limit in seconds.
    :type t_max: float, optional
    :param mz_min: Minimum m/z value for filtering peaks.
    :type mz_min: float, optional
    :param mz_max: Maximum m/z value for filtering peaks.
    :type mz_max: float, optional
    :return: A dictionary with keys ``mz``, ``area``, ``height``, ``match``.
             Returns None if no peaks are found or if an error occurs.
    :rtype: dict or None
    """
    # Prepare query parameters
    query_params = {
        "areas": str(areas).lower(),
        "heights": str(heights).lower(),
        "average": str(average).lower(),
        "matches": str(matches).lower(),
        **{
            k: v
            for k, v in {
                "t_min": t_min,
                "t_max": t_max,
                "mz_min": mz_min,
                "mz_max": mz_max,
            }.items()
            if v is not None
        },
    }

    # Make the GET request to the API endpoint with query parameters
    resp = api_get(
        url=mascope_url,
        path=f"samples/{sample_item_id}/peaks",
        access_token=access_token,
        params=query_params,
    )

    # Check if the API request was successful
    if not resp:
        logger.error(
            f"Failed to retrieve peaks for sample {sample_item_id} from {mascope_url}."
        )
        return None

    # Parse the content of the response
    content = json.loads(resp.content)
    if not (peaks_data := content.get("data", None)):
        logger.error(f"No peaks found for sample {sample_item_id}.")
        return None

    return peaks_data


@_deprecated("MascopeClient().samples.get_peak_timeseries(sample_id, mz)")
def get_sample_peak_timeseries(
    mascope_url: str,
    access_token: str,
    sample_item_id: str,
    peak_mz: float,
    peak_mz_tolerance_ppm: float = 1.0,
    t_min: float | None = None,
    t_max: float | None = None,
) -> dict | None:
    """Get timeseries data for the specified peak of the sample from the Mascope API.

    This function uses the sample-based endpoint that provides sample polarity filtering
    and time limits controls based on the sample item's acquisition parameters.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_item_id: The ID of the sample item.
    :type sample_item_id: str
    :param peak_mz: The m/z of the peak to request timeseries for.
    :type peak_mz: float
    :param peak_mz_tolerance_ppm: The m/z tolerance (ppm), defaults to 1.0.
    :type peak_mz_tolerance_ppm: float, optional
    :param t_min: Minimum time limit in seconds.
    :type t_min: float, optional
    :param t_max: Maximum time limit in seconds.
    :type t_max: float, optional
    :return: A dictionary with keys ``mz``, ``height``, ``time``.
             Returns None if no timeseries data is found or if an error occurs.
    :rtype: dict or None
    """
    # Prepare the request body
    body = {
        "peak_mz": peak_mz,
        "peak_mz_tolerance_ppm": peak_mz_tolerance_ppm,
        **{k: v for k, v in {"t_min": t_min, "t_max": t_max}.items() if v is not None},
    }

    # Check if the API request was successful
    if not (
        resp := api_post(
            url=mascope_url,
            path=f"samples/{sample_item_id}/peaks/timeseries",
            access_token=access_token,
            data=body,
        )
    ):
        logger.error(
            f"Failed to retrieve peak timeseries data for sample {sample_item_id}, m/z {peak_mz}"
        )
        return None

    # Parse the content of the response
    content = json.loads(resp.content)
    if not (timeseries_data := content.get("data", None)):
        logger.error(
            f"No timeseries data found for sample {sample_item_id}, m/z {peak_mz}"
        )
        return None

    return timeseries_data


@_deprecated("MascopeClient().samples.get_spectrum(sample_id)")
def get_sample_spectrum(
    mascope_url: str,
    access_token: str,
    sample_item_id: str,
    t_min: float | None = None,
    t_max: float | None = None,
    mz_min: float | None = None,
    mz_max: float | None = None,
) -> dict | None:
    """Get spectrum data from a sample with automatic polarity filtering.

    This function uses the sample-based endpoint that provides automatic polarity filtering
    based on the sample's metadata, ensuring only scans matching the sample's polarity are included.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_item_id: The ID of the sample item.
    :type sample_item_id: str
    :param t_min: Minimum time limit in seconds.
    :type t_min: float, optional
    :param t_max: Maximum time limit in seconds.
    :type t_max: float, optional
    :param mz_min: Minimum m/z value for filtering.
    :type mz_min: float, optional
    :param mz_max: Maximum m/z value for filtering.
    :type mz_max: float, optional
    :return: A dictionary with keys ``mz``, ``intensity``, ``intensity_unit``.
             Returns None if no spectrum data is found or if an error occurs.
    :rtype: dict or None
    """
    # Prepare query parameters
    query_params = {
        k: v
        for k, v in {
            "t_min": t_min,
            "t_max": t_max,
            "mz_min": mz_min,
            "mz_max": mz_max,
        }.items()
        if v is not None
    }

    # Make the GET request to the API endpoint with query parameters
    resp = api_get(
        url=mascope_url,
        path=f"samples/{sample_item_id}/spectrum",
        access_token=access_token,
        params=query_params,
    )

    # Check if the API request was successful
    if not resp:
        logger.error(
            f"Failed to retrieve spectrum data for sample {sample_item_id} from {mascope_url}."
        )
        return None

    # Parse the content of the response
    content = json.loads(resp.content)
    if not (spectrum_data := content.get("data", None)):
        logger.error(f"No spectrum data found for sample {sample_item_id}.")
        return None

    return spectrum_data


@_deprecated("MascopeClient().samples.get_spectra(sample_ids)")
def get_samples_spectra(
    mascope_url: str,
    access_token: str,
    sample_item_ids: list[str],
    t_min: float | None = None,
    t_max: float | None = None,
    mz_min: float | None = None,
    mz_max: float | None = None,
) -> list[dict[str, list]] | None:
    """Get averaged spectra for a list of sample items.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_item_ids: List of sample item IDs.
    :type sample_item_ids: list[str]
    :param t_min: Minimum time limit in seconds.
    :type t_min: float | None, optional
    :param t_max: Maximum time limit in seconds.
    :type t_max: float | None, optional
    :param mz_min: Minimum m/z value for filtering.
    :type mz_min: float | None, optional
    :param mz_max: Maximum m/z value for filtering.
    :type mz_max: float | None, optional
    :return: A list of spectrum dictionaries.
             Returns None if no spectrum data is found or if an error occurs.
    :rtype: list[dict[str, list]] | None
    """
    query_params = {
        k: v
        for k, v in {
            "sample_item_ids": sample_item_ids,
            "t_min": t_min,
            "t_max": t_max,
            "mz_min": mz_min,
            "mz_max": mz_max,
        }.items()
        if v is not None
    }

    response = api_get(
        url=mascope_url,
        path="samples/spectra",
        access_token=access_token,
        params=query_params,
    )

    # Check if the API request was successful
    if not response:
        logger.error(
            f"Failed to retrieve spectrum data for samples {sample_item_ids} from {mascope_url}."
        )
        return None

    content = json.loads(response.content)
    if not (spectrum_data := content.get("data", None)):
        logger.error(f"No spectrum data found for samples {sample_item_ids}.")
        return None

    return spectrum_data


@_deprecated("MascopeClient().samples.get_centroids(sample_ids)")
def get_sample_centroids_per_scan(
    mascope_url: str,
    access_token: str,
    sample_item_ids: list[str],
) -> dict | None:
    """Get centroids for a list of sample items.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_item_ids: List of sample item IDs.
    :type sample_item_ids: list[str]
    :return: A dictionary containing the centroids data for each sample item ID.
    :rtype: dict | None
    """
    params = {
        "sample_item_ids": sample_item_ids,
    }
    resp = api_get(
        url=mascope_url,
        path="samples/centroids",
        access_token=access_token,
        params=params,
    )

    # Check if the API request was successful
    if not resp:
        logger.error(
            f"Failed to retrieve centroids for sample items {sample_item_ids} from {mascope_url}."
        )
        return None

    # Parse the content of the response
    content = json.loads(resp.content)
    if not (centroids_data := content.get("data", None)):
        logger.error(f"No centroids data found for sample items {sample_item_ids}.")
        return None
    return centroids_data


##################
# Sample files API


def get_sample_file_peaks(
    mascope_url: str,
    access_token: str,
    sample_file_id: str,
    areas: bool = True,
    heights: bool = True,
) -> dict:
    """Get peaks of a given sample file, with options to include areas and/or heights.

    .. deprecated::
        Use :func:`get_sample_peaks` instead for enhanced polarity filtering and time/m/z range controls.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_file_id: The ID of the sample file.
    :type sample_file_id: str
    :param areas: If True, include peak areas. Defaults to True.
    :type areas: bool, optional
    :param heights: If True, include peak heights. Defaults to True.
    :type heights: bool, optional
    :return: A dictionary with keys ``mz``, ``area``, ``height``.
             Returns None if no peaks are found or if an error occurs.
    :rtype: dict or None
    """
    # Deprecation warning
    warnings.warn(
        "get_sample_file_peaks is deprecated and will be removed in a future releases. "
        "Use get_sample_peaks instead for sample-based polarity filtering and time or m/z range controls.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Prepare query parameters for areas and heights
    query_params = {
        "areas": str(areas).lower(),  # Convert bool to string (lowercase)
        "heights": str(heights).lower(),  # Convert bool to string (lowercase)
    }
    # Make API request with query parameters
    resp = api_get(
        url=mascope_url,
        path=f"sample/files/{sample_file_id}/peaks",
        access_token=access_token,
        params=query_params,
    )
    # Check if the API request was successful
    if not resp:
        logger.error(
            f"Failed to retrieve peaks for sample file with ID {sample_file_id} from {mascope_url}."
        )
        return None

    # Parse the content of the response
    content = json.loads(resp.content)
    peaks_data = content.get("data", None)

    if not peaks_data:
        logger.error(f"No peaks found for sample file with ID {sample_file_id}.")
        return None

    # Return the peaks data
    return peaks_data


def get_sample_file_peak_timeseries(
    mascope_url: str,
    access_token: str,
    sample_file_id: str,
    peak_mz: float,
    peak_mz_tolerance_ppm: float = None,
) -> dict:
    """Get timeseries data for the specified peak of the sample file.

    .. deprecated::
        Use :func:`get_sample_peak_timeseries` instead for enhanced polarity and time filtering.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_file_id: The ID of the sample file.
    :type sample_file_id: str
    :param peak_mz: The m/z of the peak.
    :type peak_mz: float
    :param peak_mz_tolerance_ppm: The m/z tolerance (ppm). Defaults to None.
    :type peak_mz_tolerance_ppm: float, optional
    :return: A dictionary with keys ``mz``, ``height``, ``time``.
             Returns None if no timeseries data is found or if an error occurs.
    :rtype: dict or None
    """
    # Issue deprecation warning
    warnings.warn(
        "get_sample_file_peak_timeseries is deprecated and will be removed in a future release. "
        "Use get_sample_peak_timeseries instead for sample-based polarity filtering and time limits controls.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Prepare the payload for the POST request
    body = (
        {"peak_mz": peak_mz, "peak_mz_tolerance_ppm": peak_mz_tolerance_ppm}
        if peak_mz_tolerance_ppm is not None
        else {"peak_mz": peak_mz}
    )
    resp = api_post(
        url=mascope_url,
        path=f"sample/files/{sample_file_id}/peaks/timeseries",
        access_token=access_token,
        data=body,
    )
    # Check if the API request was successful
    if not resp:
        logger.error(
            f"Failed to retrieve peak timeseries data from {mascope_url} for file ID {sample_file_id} and peak m/z {peak_mz}."
        )
        return None

    # Parse the content of the response
    content = json.loads(resp.content)
    timeseries_data = content.get("data", None)

    if not timeseries_data:
        logger.error(
            f"No timeseries data found for sample file with ID {sample_file_id} and peak m/z {peak_mz}."
        )
        return None

    # Return the timeseries data
    return timeseries_data


def get_sample_file_spectrum(
    mascope_url: str,
    access_token: str,
    sample_file_id: str,
    t_min: float = None,
    t_max: float = None,
    mz_min: float = None,
    mz_max: float = None,
) -> dict:
    """Get the mass spectrum from a specified sample file.

    .. deprecated::
        Use :func:`get_sample_spectrum` instead for enhanced polarity filtering.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_file_id: The ID of the sample file.
    :type sample_file_id: str
    :param t_min: Start of the time range. Defaults to None.
    :type t_min: float, optional
    :param t_max: End of the time range. Defaults to None.
    :type t_max: float, optional
    :param mz_min: Start of the m/z range. Defaults to None.
    :type mz_min: float, optional
    :param mz_max: End of the m/z range. Defaults to None.
    :type mz_max: float, optional
    :return: A dictionary with keys ``mz``, ``intensity``.
             Returns None if no spectrum data is found or if an error occurs.
    :rtype: dict or None
    """
    # Deprecation warning
    warnings.warn(
        "get_sample_file_spectrum is deprecated and will be removed in a future release. "
        "Use get_sample_spectrum instead for sample-based polarity filtering capabilities.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Prepare query parameters as a dictionary
    query_params = {}
    if t_min is not None:
        query_params["t_min"] = t_min
    if t_max is not None:
        query_params["t_max"] = t_max
    if mz_min is not None:
        query_params["mz_min"] = mz_min
    if mz_max is not None:
        query_params["mz_max"] = mz_max

    # Make the GET request to the API endpoint with query parameters
    resp = api_get(
        url=mascope_url,
        path=f"sample/files/{sample_file_id}/spectrum",
        access_token=access_token,
        params=query_params,
    )

    # Check if the API request was successful
    if not resp:
        logger.error(
            f"Failed to retrieve spectrum data for sample file with ID {sample_file_id} from {mascope_url}."
        )
        return None

    # Parse the content of the response
    content = json.loads(resp.content)
    spectrum_data = content.get("data", None)

    if not spectrum_data:
        logger.error(
            f"No spectrum data found for sample file with ID {sample_file_id} and the given time or m/z ranges."
        )
        return None

    return spectrum_data


def get_sample_file_instrument_config(
    mascope_url: str,
    access_token: str,
    sample_file_name: str,
) -> dict:
    """Retrieve the instrument config for a sample file using its filename.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_file_name: The name of the sample file.
    :type sample_file_name: str
    :return: The instrument config dictionary, or None if not found.
    :rtype: dict or None
    """
    resp = api_get(
        url=mascope_url,
        path=f"instrument_configs/by_filename/{sample_file_name}",
        access_token=access_token,
    )
    if not resp:
        logger.error(
            f"Failed to retrieve instrument config for filename {sample_file_name}."
        )
        return None

    content = json.loads(resp.content)
    instrument_config = content.get("data", None)
    if not instrument_config:
        logger.error(f"No instrument config found for filename {sample_file_name}.")
        return None

    return instrument_config


def get_sample_file_metadata(
    mascope_url: str,
    access_token: str,
    sample_file_id: str,
) -> dict | None:
    """Retrieve metadata for a specific sample file by its ID.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param sample_file_id: The ID of the sample file.
    :type sample_file_id: str
    :return: Metadata dictionary for the sample file, or None if not found or error.
    :rtype: dict or None
    """
    resp = api_get(
        url=mascope_url,
        path=f"sample/files/{sample_file_id}/metadata",
        access_token=access_token,
    )
    if not resp:
        logger.error(
            f"Failed to retrieve metadata for sample file with ID {sample_file_id} from {mascope_url}."
        )
        return None

    content = resp.json()
    metadata = content.get("data", None)
    if not metadata:
        logger.error(f"No metadata found for sample file with ID {sample_file_id}.")
        return None

    return metadata


###########################
# Ionization mechanisms API


@_deprecated("MascopeClient().ionization.list()")
def get_ionization_mechanisms(mascope_url: str, access_token: str) -> list[dict]:
    """Get ionization mechanisms from the Mascope API.

    This function retrieves the list of ionization mechanisms available in the Mascope instance.

    :param mascope_url: Base URL of the Mascope API.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :return: Ionization mechanisms data as a list of dictionaries.
    :rtype: list[dict]
    """
    resp = api_get(
        url=mascope_url, path="ionization_mechanisms", access_token=access_token
    )
    # Check if the API request was successful
    if not resp:
        logger.error(f"Failed to get ionization mechanisms from {mascope_url}")
        return None

    # Successfully fetched ionization mechanisms, extract 'data' from the response JSON
    content = resp.json()
    return content.get("data", [])


##############
# ChemInfo API


@_deprecated("MascopeClient().cheminfo.query_by_mz(mz, mechanism_ids)")
def get_cheminfo_by_mz(
    mascope_url: str,
    access_token: str,
    mz: float,
    ionization_mechanism_ids: list[str],
    formula_ranges: str = "C0-100 H0-100 O0-100 N0-100",
    mz_tolerance: float = 30.0,
    limit: int = 20,
) -> list[dict]:
    """Query ChemInfo service for potential elemental compositions for a given m/z value.

    :param mascope_url: Base URL of the Mascope API.
    :type mascope_url: str
    :param access_token: Authorization token for API access.
    :type access_token: str
    :param mz: The m/z value to query for.
    :type mz: float
    :param ionization_mechanism_ids: List of ionization mechanism IDs.
    :type ionization_mechanism_ids: list[str]
    :param formula_ranges: Ranges of elements to consider.
                           Defaults to "C0-100 H0-100 O0-100 N0-100".
    :type formula_ranges: str, optional
    :param mz_tolerance: The m/z tolerance in ppm. Defaults to 30.0.
    :type mz_tolerance: float, optional
    :param limit: Maximum number of results. Defaults to 20.
    :type limit: int, optional
    :return: List of dictionaries containing potential elemental compositions.
    :rtype: list[dict]
    """
    query_params = {
        "mz": mz,
        "mz_precision": mz_tolerance,
        "formula_ranges": formula_ranges,
        "ionization_mechanism_ids": ionization_mechanism_ids,
        "limit": limit,
    }
    # Make the POST request to the instrument_functions endpoint
    resp = api_post(
        url=mascope_url,
        path="cheminfo/mz/query",
        access_token=access_token,
        data=query_params,
    )
    # Check if the API request was successful
    if not resp:
        logger.error(f"Failed to retrieve cheminfo for m/z {mz} via {mascope_url}.")
        return None

    # Successfully fetched cheminfo, extract 'data' from the response JSON
    response_json = resp.json()
    return response_json.get("data", [])
