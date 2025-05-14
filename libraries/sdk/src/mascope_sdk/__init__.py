import json
import requests
import warnings
from requests.exceptions import HTTPError, Timeout, RequestException
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# TODO add the message to every response in the fastapi, including success with number of results.

# Suppress only the InsecureRequestWarning from requests
warnings.simplefilter("ignore", InsecureRequestWarning)


def api_get(url: str, path: str, access_token: str, params: dict = None):
    """
    Send a GET request to the specified API endpoint with optional query parameters.

    :param url: The base URL of the server.
    :type url: str
    :param path: The specific API path to be appended to the base URL.
    :type path: str
    :param access_token: Authorization token for API access
    :type access_token: str
    :param params: A dictionary of query parameters to include in the request.
    :type params: dict, optional
    :return: The response object if the request was successful, otherwise None.
    :rtype: requests.Response or None
    """
    full_url = url + "/api/" + path
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Service-Name": "mascope_sdk",
        }

        # Send GET request with query parameters (if provided)
        resp = requests.get(
            full_url, params=params, headers=headers, verify=False, timeout=30
        )
        resp.raise_for_status()  # Raise HTTPError for bad responses
        message = json.loads(resp.content).get("message", None)
        if message is not None:
            print(message)
    except HTTPError as http_err:
        if resp.status_code == 401 or resp.status_code == 403:
            response = json.loads(resp.content)
            error_message = response.get("detail", {}).get("error_message", None)
            print(f"{error_message} Please check your API token.")
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
            print(
                f"HTTP error: Unable to retrieve data from {full_url}. \nDetails: {http_err} \nServer message: {error_message}"
            )
        return None
    except Timeout:
        print(f"Timeout error: The request to {full_url} timed out.")
        return None
    except RequestException as req_err:
        print(
            f"Connection error: Could not connect to {full_url}. Please check the URL and your network connection. \nDetails: {req_err}"
        )
        return None
    except Exception as e:
        print(
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
    :param access_token: Authorization token for API access
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
            "X-Service-Name": "mascope_sdk",
        }
        resp = requests.post(
            full_url, data=json.dumps(data), headers=headers, verify=False, timeout=30
        )
        resp.raise_for_status()  # Raise HTTPError for bad responses
        message = json.loads(resp.content).get("message", None)
        if message is not None:
            print(message)
    except HTTPError as http_err:
        if resp.status_code == 401 or resp.status_code == 403:
            response = json.loads(resp.content)
            error_message = response.get("detail", {}).get("error_message", None)
            print(f"{error_message} Please check your API token.")
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
            print(
                f"HTTP error: Unable to retrieve data from {full_url}. \nDetails: {http_err} \nServer message: {error_message}"
            )
        return None
    except Timeout:
        print(f"Timeout error: The request to {full_url} timed out.")
        return None
    except RequestException as req_err:
        print(
            f"Connection error: Could not connect to {full_url}. Please check the URL and your network connection. \nDetails: {req_err}"
        )
        return None
    except Exception as e:
        print(
            f"Error: An unexpected error occurred while trying to reach {full_url}. \nDetails: {str(e)}"
        )
        return None
    return resp


def api_post_file(
    url: str,
    path: str,
    access_token: str,
    filepath: str,
    service_name: str = "mascope_sdk",
):
    """Send a POST request to the specified API endpoint with a path file to be uploaded.

    :param url: The base URL of the server.
    :type url: str
    :param path: The specific API path to be appended to the base URL.
    :type path: str
    :param access_token: Authorization token for API access
    :type access_token: str
    :param filepath: Path to the file to be uploaded
    :type filepath: str
    :param service_name: The name of the service making the request, defaults to "mascope_sdk".
    :type service_name: str, optional
    :return: The response object if the request was successful, otherwise None.
    :rtype: requests.Response or None
    """
    full_url = url + "/api/" + path
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Service-Name": service_name,
        }
        with open(filepath, "rb") as file:
            resp = requests.post(
                full_url,
                files={"file": file},
                headers=headers,
                verify=False,
                timeout=30,
            )
        resp.raise_for_status()  # Raise HTTPError for bad responses
        message = json.loads(resp.content).get("message", None)
        if message is not None:
            print(message)
    except HTTPError as http_err:
        if resp.status_code == 401 or resp.status_code == 403:
            response = json.loads(resp.content)
            error_message = response.get("detail", {}).get("error_message", None)
            print(f"{error_message} Please check your API token.")
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
            print(
                f"HTTP error: Unable to retrieve data from {full_url}. \nDetails: {http_err} \nServer message: {error_message}"
            )
        return None
    except Timeout:
        print(f"Timeout error: The request to {full_url} timed out.")
        return None
    except RequestException as req_err:
        print(
            f"Connection error: Could not connect to {full_url}. Please check the URL and your network connection. \nDetails: {req_err}"
        )
        return None
    except Exception as e:
        print(
            f"Error: An unexpected error occurred while trying to reach {full_url}. \nDetails: {str(e)}"
        )
        return None
    return resp


################
# Workspaces API


def get_workspaces(mascope_url: str, access_token: str) -> list:
    """Get Mascope workspaces from a URL

    :param mascope_url: Mascope URL
    :type mascope_url: str
    :param access_token: Authorization token for API access
    :type access_token: str
    :return: List of workspace dictionaries.
    :rtype: list
    """
    resp = api_get(url=mascope_url, path="workspaces", access_token=access_token)
    # Check if the request was successful
    if not resp:
        print(
            f"Failed to retrieve workspaces from {mascope_url}. Please check the URL and try again."
        )
        return []

    content = json.loads(resp.content)
    workspaces = content.get("data", [])
    if not workspaces:
        print("No workspaces found. Please create a new workspace.")

    return workspaces


####################
# Sample batches API


def get_sample_batches(mascope_url: str, access_token: str, workspace_id: str) -> list:
    """
    Get Mascope sample batches of a workspace.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access
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
        print(
            f"Failed to retrieve sample batches from {mascope_url}. Please check the URL and try again."
        )
        return []

    content = json.loads(resp.content)
    batches = content.get("data", [])

    if not batches:
        print("No sample batches found. Please create a new sample batch.")

    return batches


def get_sample_batch_data(
    mascope_url: str,
    access_token: str,
    sample_batch_id: str,
) -> dict:
    """
    Retrieve detailed data for all samples in a sample batch.

    This function interacts with the Mascope API to fetch comprehensive data
    for a given sample batch. It retrieves data for samples and combinned match/targets data
    for compounds, ions, isotopes and interferences (included to isotopes).

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access
    :type access_token: str
    :param sample_batch_id: The ID of the sample batch to retrieve data for.
    :type sample_batch_id: str
    :return: A dictionary containing:
             - `result`: Summary statistics about the retrieved data.
             - `sample_batch`: Information about the sample batch.
             - `samples`: A list of samples within the batch. Combination of samples (sample_item + sample_file) and match_samples
             - `compounds`: Data for compounds. Combination of match_compounds and target_compounds
             - `ions`: Data for ions. Combination of match_ions and target_ions
             - `isotopes`: Data for isotopes. Combination of match_isotopes, match_interferences, and target_isotopes
             Returns an empty dictionary if the request fails or no data is found.
    :rtype: dict
    """
    # Step 1: Call the API to get the batch data (stored in database)
    resp = api_get(
        url=mascope_url,
        path=f"match/targets/batch/{sample_batch_id}",
        access_token=access_token,
    )
    if not resp:
        print(
            f"Failed to retrieve match data for sample batch with ID {sample_batch_id}."
        )
        return {}

    # Step 2: Parse the response content
    batch_data = json.loads(resp.content)
    if not batch_data:
        print(f"No data returned for sample batch with ID {sample_batch_id}.")
        return {}

    # Step 3: Extract relevant information from the aggregate match data
    result = batch_data.get("result", {})
    sample_batch = batch_data.get("data", {}).get("sample_batch", {})
    samples = batch_data.get("data", {}).get("samples", [])
    compounds = batch_data.get("data", {}).get("compounds", [])
    ions = batch_data.get("data", {}).get("ions", [])
    isotopes = batch_data.get("data", {}).get("isotopes", [])

    # Step 4: Build the response structure
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


def get_samples(mascope_url: str, access_token: str, sample_batch_id: str) -> list:
    """
    Get Mascope samples of the specified sample batch.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access
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
        print(
            f"Failed to retrieve samples from {mascope_url}. Please check the URL and try again."
        )
        return []

    content = json.loads(resp.content)
    samples = content.get("data", [])
    if not samples:
        print(f"No samples found for sample batch with ID {sample_batch_id}.")

    return samples


def get_sample(mascope_url: str, access_token: str, sample_item_id: str) -> dict:
    """
    Get details of a specific sample by its ID.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access
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
        print(f"Failed to retrieve sample details from {mascope_url}.")
        return None

    sample = json.loads(resp.content)
    if not sample:
        print(f"No sample with ID {sample_item_id} found.")
    return sample


def get_sample_compound_matches(
    mascope_url: str,
    access_token: str,
    sample_item_id: str,
    target_compound_formula: str,
    target_compound_name: str = "Unknown Compound",
    match_params: dict = None,
) -> dict:
    """
    Retrieves matches for compounds within a sample based on a target compound formula,
    applying specified filter parameters to filter the matches.

    :param mascope_url: Base URL of the Mascope API.
    :type mascope_url: str
    :param access_token: Authorization token for API access
    :type access_token: str
    :param sample_item_id: Unique identifier of the sample item to analyze.
    :type sample_item_id: str
    :param target_compound_formula: Chemical formula of the target compound.
    :type target_compound_formula: str
    :param target_compound_name: The name of the target compound, defaults to "Unknown Compound"
    :type target_compound_name: str, optional
    :param match_params: Parameters to filter the match results, affecting which matches are considered significant.
                          Should be a dictionary representing a MatchParams Pydantic model.
    :type match_params: dict, optional
    :return: A dictionary containing the match data (compound->ions->isotopes).
             Returns None if no match data is found or if an error occurs.
    :rtype: dict

    Example of target compound and filter parameters data:
        "target_compound_formula": "C6H12N2O6",
        "target_compound_name": "Formic acid", # compound name is optional
        "match_params": {
            "mz_tolerance": 72,
            "isotope_ratio_tolerance": 0.2,
            "peak_min_intensity": 0.0,
            "min_isotope_abundance": 0.15,
            "min_isotope_correlation": 0.7,
            "probable_match_threshold": 0.8,
            "possible_match_threshold": 0.4,
        }
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
        print(
            f"Failed to retrieve compound '{target_compound_formula}' match data for for sample item ID {sample_item_id} from {mascope_url}."
        )
        return None

    # Parse the content of the response
    response_json = resp.json()
    match_data = response_json.get("data", None)

    if not match_data:
        print(
            f"No compound matches found for sample item ID {sample_item_id} and target compound {target_compound_formula}."
        )
        return None

    return match_data


##################
# Sample files API


def get_sample_file_peaks(
    mascope_url: str,
    access_token: str,
    sample_file_id: str,
    areas: bool = True,
    heights: bool = True,
) -> dict:
    """
    Get peaks of a given sample file, with options to include areas and/or heights.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access
    :type access_token: str
    :param sample_file_id: The ID of the sample file from which to retrieve peaks.
    :type sample_file_id: str
    :param areas: If True, include peak areas in the response, defaults to True.
    :type areas: bool, optional
    :param heights: If True, include peak heights in the response, defaults to True.
    :type heights: bool, optional
    :return: A dictionary with keys:
        - "mz": list of m/z values of the peaks in the sample file
        - "area": list of peak areas (if requested)
        - "height": list of peak heights (if requested)
        Returns None if no peaks are found or if an error occurs.
    :rtype: dict or None
    """
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
        print(
            f"Failed to retrieve peaks for sample file with ID {sample_file_id} from {mascope_url}."
        )
        return None

    # Parse the content of the response
    content = json.loads(resp.content)
    peaks_data = content.get("data", None)

    if not peaks_data:
        print(f"No peaks found for sample file with ID {sample_file_id}.")
        return None

    # Return the peaks data
    return peaks_data


def get_sample_file_peak_noise(
    mascope_url: str,
    access_token: str,
    sample_file_id: str,
    mzs: list[float],
    t_min: float = None,
    t_max: float = None,
    ppm: int = 1,
    polarity: str = None,
) -> dict:
    """
    Get noise values for given peak m/z values in a sample file.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access
    :type access_token: str
    :param sample_file_id: The ID of the sample file.
    :type sample_file_id: str
    :param mzs: List of peak m/z values to compute noise for.
    :type mzs: list[float]
    :param t_min: Start time (optional).
    :type t_min: float, optional
    :param t_max: End time (optional).
    :type t_max: float, optional
    :param ppm: ppm precision for binning, defaults to 1.
    :type ppm: int, optional
    :param polarity: Polarity of the scans, "+" or "-", optional.
    :type polarity: str, optional
    :return: Dictionary with m/z values and corresponding noise values, or None if request fails.
    :rtype: dict or None
    """
    body = {
        "mzs": mzs,
        "t_min": t_min,
        "t_max": t_max,
        "ppm": ppm,
        "polarity": polarity,
    }
    # Remove None values from body
    body = {k: v for k, v in body.items() if v is not None}

    resp = api_post(
        url=mascope_url,
        path=f"sample/files/{sample_file_id}/peaks/noise",
        access_token=access_token,
        data=body,
    )
    if not resp:
        print(
            f"Failed to retrieve peak noise data for sample file with ID {sample_file_id} from {mascope_url}."
        )
        return None

    content = resp.json()
    peak_noise_data = content.get("data", None)

    if not peak_noise_data:
        print(f"No peak noise data found for sample file with ID {sample_file_id}.")
        return None

    return peak_noise_data


def get_sample_file_peak_timeseries(
    mascope_url: str,
    access_token: str,
    sample_file_id: str,
    peak_mz: float,
    peak_mz_tolerance_ppm: float = None,
) -> dict:
    """Get timeseries data for the specified peak of the sample file from the Mascope API.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access
    :type access_token: str
    :param sample_file_id: The ID of the sample file from which to retrieve peak timeseries data.
    :type sample_file_id: str
    :param peak_mz: The m/z of the peak to request timeseries for.
    :type peak_mz: float
    :param peak_mz_tolerance_ppm: The m/z tolerance within which the peak should be compared (ppm), defaults to None.
    :type peak_mz_tolerance_ppm: float, optional
    :return: A dictionary with keys:
        - "mz": m/z of the peak in sample file (None if no peak within tolerance)
        - "height": list of peak intensity at time points (empty if no peak within tolerance)
        - "time": list of time coordinates (empty if no peak within tolerance)
        Returns None if no timeseries data is found or if an error occurs.
    :rtype: dict or None
    """
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
        print(
            f"Failed to retrieve peak timeseries data from {mascope_url} for file ID {sample_file_id} and peak m/z {peak_mz}."
        )
        return None

    # Parse the content of the response
    content = json.loads(resp.content)
    timeseries_data = content.get("data", None)

    if not timeseries_data:
        print(
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
    """
    Get the mass spectrum from a specified sample file within optional time and m/z ranges.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access
    :type access_token: str
    :param sample_file_id: The ID of the sample file from which to retrieve the spectrum.
    :type sample_file_id: str
    :param t_min: Start of the time range, defaults to None.
    :type t_min: float, optional
    :param t_max: End of the time range, defaults to None.
    :type t_max: float, optional
    :param mz_min: Start of the m/z range, defaults to None.
    :type mz_min: float, optional
    :param mz_max: End of the m/z range, defaults to None.
    :type mz_max: float, optional
    :return: A dictionary with keys:
        - "mz": list of m/z values
        - "intensity": list of intensity values
        - Optional: "results" and "spectrum_count" if available.
        Returns None if no spectrum data is found or if an error occurs.
    :rtype: dict or None
    """
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
        print(
            f"Failed to retrieve spectrum data for sample file with ID {sample_file_id} from {mascope_url}."
        )
        return None

    # Parse the content of the response
    content = json.loads(resp.content)
    spectrum_data = content.get("data", None)

    if not spectrum_data:
        print(
            f"No spectrum data found for sample file with ID {sample_file_id} and the given time or m/z ranges."
        )
        return None

    return spectrum_data


def get_sample_file_instrument_config(
    mascope_url: str,
    access_token: str,
    sample_file_name: str,
) -> dict:
    """
    Retrieve the instrument config for a sample file using its filename.

    :param mascope_url: The base URL of the Mascope instance.
    :type mascope_url: str
    :param access_token: Authorization token for API access
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
        print(f"Failed to retrieve instrument config for filename {sample_file_name}.")
        return None

    content = json.loads(resp.content)
    instrument_config = content.get("data", None)
    if not instrument_config:
        print(f"No instrument config found for filename {sample_file_name}.")
        return None

    return instrument_config


##########################
# Instrument functions API


def create_instrument_function(
    mascope_url: str,
    access_token: str,
    instrument: str,
    datetime_utc: str,
    peakshape: dict,
    resolution_function: list,
) -> dict:
    """
    Create a new instrument function record in the database.

    :param mascope_url: Base URL of the Mascope API.
    :type mascope_url: str
    :param access_token: Authorization token for API access
    :type access_token: str
    :param instrument: Name of the instrument.
    :type instrument: str
    :param datetime_utc: UTC timestamp of the instrument function.
    :type datetime_utc: str
    :param peakshape: Peak shape data containing 'x' and 'y' lists.
    :type peakshape: dict
    :param resolution_function: List containing resolution function parameters.
    :type resolution_function: list
    :return: The created instrument function details as received from the API response.
             Returns None if creation failed or an error occurs.
    :rtype: dict or None

    Example instrument function input data:
        instrument_function_data = {
            "instrument": "KLTOF1",
            "datetime_utc": "2024-04-04T07:51:00.717774",
            "peakshape": {
                "x": [-30.0, -29.9, -29.8, 29.8, 29.9, 30.0,],
                "y": [0.0, 3.0326e-06, 4.8616e-06, 7.4314e-03, 1.2687e-02, 2.2572e-02,]
            },
            "resolution_function": [0.0001098, 0.0003524]
        }
    """
    # Construct the request body based on the function parameters
    data = {
        "instrument": instrument,
        "datetime_utc": datetime_utc,
        "peakshape": peakshape,
        "resolution_function": resolution_function,
    }

    # Make the POST request to the instrument_functions endpoint
    resp = api_post(
        url=mascope_url,
        path="instrument_functions",
        access_token=access_token,
        data=data,
    )
    # Check if the API request was successful
    if not resp:
        print(f"Failed to create instrument function from {mascope_url}")
        return None

    # Successfully created the instrument function, extract 'data' from the response JSON
    response_json = resp.json()
    created_instrument_function = response_json.get("data", None)

    if not created_instrument_function:
        print(f"Failed to create instrument function. Status code: {resp.status_code}")
        return None

    return created_instrument_function
