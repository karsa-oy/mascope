import json
import ipywidgets as widgets
from IPython.display import display
import requests
import urllib3
import pandas as pd


# hide self-signed certificate warnings
urllib3.disable_warnings()


def api_get(url: str, path: str):
    try:
        url = url + "/api/" + path
        resp = requests.get(url, verify=False, timeout=15)
    except Exception as e:
        # print(f"GET {url} failed: {str(e)}")
        return None
    return resp


def api_post(url: str, path: str, data: dict):
    try:
        url = url + "/api/" + path
        resp = requests.post(url, data=json.dumps(data), verify=False, timeout=30)
    except Exception as e:
        # print(f"POST {url} failed: {str(e)}")
        return None
    return resp


def select_url(ctx):
    def on_select(change):
        if change.new == "...":
            return
        try:
            resp = requests.get(change.new, verify=False, timeout=5)
        except Exception as e:
            print(f"{change.new} not available: {str(e)}")
            return
        print(f"Selected {ctx['title']} = {change.new}")
        ctx[ctx["title"]] = change.new
        return

    print("Select URL")
    style = {"description_width": "initial"}
    dropdown = widgets.Dropdown(
        options=["..."] + ctx["url_list"], description=ctx["title"], style=style
    )
    dropdown.observe(on_select, names="value")
    display(dropdown)
    return dropdown


def select_workspace(ctx):
    def on_select(change):
        if change.new == "...":
            return
        print(f"Workspace '{change.new}' selected")
        ctx["workspace"] = wks[change.new]
        return

    print("Select Workspace")
    resp = api_get(ctx["mascope_url"], "workspaces?sort=workspace_name")
    # print(resp.status_code, resp.content)
    content = None if resp.status_code != 200 else json.loads(resp.content)
    wks = content and content["data"] or []
    wks = dict([(w["workspace_name"], w) for w in wks])
    style = {"description_width": "initial"}
    dropdown = widgets.Dropdown(
        options=["..."] + list(wks.keys()), description="Workspaces", style=style
    )
    dropdown.observe(on_select, names="value")
    display(dropdown)
    return dropdown, wks


def select_sample_batch(ctx):
    def on_select(change):
        if change.new == "...":
            return
        print(f"Sample Batch '{change.new}' selected")
        ctx["sample_batch"] = batches[change.new]
        return

    print("Select Sample Batch")
    resp = api_get(
        ctx["mascope_url"],
        f"sample/batches?workspace_id={ctx['workspace']['workspace_id']}&sort=sample_batch_name",
    )
    # print(resp.status_code, resp.content)
    content = None if resp.status_code != 200 else json.loads(resp.content)
    batches = content and content["data"] or []
    batches = dict([(b["sample_batch_name"], b) for b in batches])
    style = {"description_width": "initial"}
    dropdown = widgets.Dropdown(
        options=["..."] + list(batches.keys()),
        description=f"{ctx['workspace']['workspace_name']} batches",
        layout={"width": "max-content"},
        style=style,
    )
    dropdown.observe(on_select, names="value")
    display(dropdown)
    return dropdown, batches


def multi_select_sample_batches(ctx):
    def on_select(change):
        if change.new == "...":
            return
        print(f"Sample Batches '{change.new}' selected")
        ctx["sample_batches"] = [batches[name] for name in change.new]
        return

    print("Select Sample Batches")
    resp = api_get(
        ctx["mascope_url"],
        f"sample/batches?workspace_id={ctx['workspace']['workspace_id']}&sort=sample_batch_name",
    )
    # print(resp.status_code, resp.content)
    content = None if resp.status_code != 200 else json.loads(resp.content)
    batches = content and content["data"] or []
    batches = dict([(b["sample_batch_name"], b) for b in batches])
    style = {"description_width": "initial"}
    multi_selector = widgets.SelectMultiple(
        options=list(batches.keys()),
        description=f"{ctx['workspace']['workspace_name']} batches",
        rows=min(10, len(batches)),
        layout={"width": "max-content"},
        style=style,
    )
    multi_selector.observe(on_select, names="value")
    display(multi_selector)
    return multi_selector, batches


def filter_params(ctx):
    style = {"description_width": "initial"}
    widget_list = []
    widget_list.append(
        widgets.IntSlider(
            value=15, min=0, max=150, step=1, description="mz_tolerance", style=style
        )
    )
    widget_list.append(
        widgets.FloatSlider(
            value=0.1,
            min=0,
            max=1,
            step=0.1,
            description="isotope_ratio_tolerance",
            style=style,
        )
    )
    widget_list.append(
        widgets.FloatSlider(
            value=0.0,
            min=0,
            max=1,
            step=0.1,
            description="peak_min_intensity",
            style=style,
        )
    )
    widget_list.append(
        widgets.FloatSlider(
            value=0.15,
            min=0,
            max=1,
            step=0.05,
            description="min_isotope_abundance",
            style=style,
        )
    )
    widget_list.append(
        widgets.FloatSlider(
            value=0.8,
            min=0,
            max=1,
            step=0.1,
            description="min_isotope_correlation",
            style=style,
        )
    )
    return


def get_batch_samples_records(
    mascope_url,
    batch_id,
    batch_name,
    batch_matches_info=True,
    match_samples=True,
    match_compounds=True,
    match_ions=True,
    match_isotopes=True,
):
    data = dict(
        sample_batch_id=batch_id,
        batch_matches_info=batch_matches_info,
        match_samples=match_samples,
        match_compounds=match_compounds,
        match_ions=match_ions,
        match_isotopes=match_isotopes,
    )
    resp = api_post(mascope_url, "samples/old", data=data)
    assert (
        resp.status_code == 200
    ), f"get_batch_samples_records('{batch_name}') response error {resp.status_code}"
    content = json.loads(resp.content)
    try:
        # content['batch_matches_info'] does not have batch creds - add
        for r in content["data"]:
            r.update({"sample_batch_id": batch_id, "sample_batch_name": batch_name})
        if batch_matches_info:
            if match_samples:
                for r in content["batch_matches_info"]["match_samples"]:
                    r.update(
                        {"sample_batch_id": batch_id, "sample_batch_name": batch_name}
                    )
            if match_compounds:
                for r in content["batch_matches_info"]["match_compounds"]:
                    r.update(
                        {"sample_batch_id": batch_id, "sample_batch_name": batch_name}
                    )
            if match_ions:
                for r in content["batch_matches_info"]["match_ions"]:
                    r.update(
                        {"sample_batch_id": batch_id, "sample_batch_name": batch_name}
                    )
            if match_isotopes:
                for r in content["batch_matches_info"]["match_isotopes"]:
                    r.update(
                        {"sample_batch_id": batch_id, "sample_batch_name": batch_name}
                    )
    except Exception as e:
        raise Exception(
            f"Error batch '{batch_name}' : {e.__class__.__name__}({str(e)})"
        )
    match_data = content.get("data", [])
    match_samples = content.get("batch_matches_info", {}).get("match_samples", [])
    match_compounds = content.get("batch_matches_info", {}).get("match_compounds", [])
    match_ions = content.get("batch_matches_info", {}).get("match_ions", [])
    match_isotopes = content.get("batch_matches_info", {}).get("match_isotopes", [])
    print(
        f"{batch_name} - "
        f"data:{len(match_data)} "
        f"samples:{len(match_samples)} "
        f"compounds:{len(match_compounds)} "
        f"ions:{len(match_ions)} "
        f"isotopes:{len(match_isotopes)}"
    )
    return {
        "data": match_data,
        "match_samples": match_samples,
        "match_compounds": match_compounds,
        "match_ions": match_ions,
        "match_isotopes": match_isotopes,
    }


def get_batch_samples_with_matches_info(ctx):
    print("get_batch_samples_with_matches_info...")
    mascope_url = ctx["mascope_url"]
    batch_id = ctx["sample_batch"]["sample_batch_id"]
    batch_name = ctx["sample_batch"]["sample_batch_name"]
    records = get_batch_samples_records(mascope_url, batch_id, batch_name)
    ctx["batch_samples_data"] = records
    return records


def get_multi_batch_samples_with_matches_info(ctx):
    print("get_multi_batch_samples_with_matches_info...")
    mascope_url = ctx["mascope_url"]
    batch_ids = [b["sample_batch_id"] for b in ctx["sample_batches"]]
    batch_names = [b["sample_batch_name"] for b in ctx["sample_batches"]]
    multi_batch_recs = None
    for i, (batch_id, batch_name) in enumerate(zip(batch_ids, batch_names)):
        print(f"{i+1}/{len(batch_ids)}  ", end="")
        recs = get_batch_samples_records(mascope_url, batch_id, batch_name)
        if multi_batch_recs is None:
            multi_batch_recs = dict((key, []) for key in recs.keys())
        for k, r in multi_batch_recs.items():
            r.extend(recs[k])
    ctx["batch_samples_data"] = multi_batch_recs
    return multi_batch_recs


def cast_batch_samples_data_to_dataframes(ctx):
    print("cast_batch_samples_data_to_dataframes...")
    dataframes = dict()
    for title, records in ctx["batch_samples_data"].items():
        dataframes[title] = pd.DataFrame(records)
    ctx["batch_samples_dataframes"] = dataframes
    return dataframes


def get_workspaces(mascope_url: str) -> list:
    """Get Mascope workspaces from a URL

    :param mascope_url: Mascope URL
    :type mascope_url: str
    :return: List workspace tuples in the form (workspace_name: str, workspace: dict)
    :rtype: list
    """
    resp = api_get(mascope_url, "workspaces")
    content = None if not resp or resp.status_code != 200 else json.loads(resp.content)
    workspaces = content and content.get("data") or []
    return [(workspace["workspace_name"], workspace) for workspace in workspaces]


def get_sample_batches(mascope_url: str, workspace_id: str) -> list:
    """Get Mascope sample batches from a URL from a workspace

    :param mascope_url: Mascope URL
    :type mascope_url: str
    :param workspace_id: Workspace ID
    :type workspace_id: str
    :return: List sample batch tuples in the form (sample_batch_name: str, sample_batch: dict)
    :rtype: list
    """
    resp = api_get(
        mascope_url,
        f"sample/batches?workspace_id={workspace_id}",
    )
    content = None if not resp or resp.status_code != 200 else json.loads(resp.content)
    batches = content and content["data"] or []
    return [
        (sample_batch["sample_batch_name"], sample_batch) for sample_batch in batches
    ]


def get_sample_batch_data(
    mascope_url: str,
    sample_batch_id: str,
    match_samples: bool = True,
    match_compounds: bool = True,
    match_ions: bool = True,
    match_isotopes: bool = True,
) -> dict:
    """Load data of a sample batch.

    Can load only sample items or also match data with different levels of aggregation.

    :param mascope_url: Mascope URL
    :type mascope_url: str
    :param sample_batch_id: Sample batch ID
    :type sample_batch_id: str
    :param match_samples: Load sample-level aggregation of match data, defaults to True
    :type match_samples: bool, optional
    :param match_compounds: Load compound-level aggregation of match data, defaults to True
    :type match_compounds: bool, optional
    :param match_ions: Load ion-level aggregation of match data, defaults to True
    :type match_ions: bool, optional
    :param match_isotopes: Load isotope-level match data, defaults to True
    :type match_isotopes: bool, optional
    :return: Loaded data as a dict with keys:
        ['sample_items_df',
        'match_samples_df',
        'match_compounds_df',
        'match_ions_df',
        'match_isotopes_df'].
        Values are instances of pd.DataFrame, empty if data is not loaded.
    :rtype: dict
    """
    request_body = dict(
        sample_batch_id=sample_batch_id,
        batch_matches_info=any(
            [match_samples, match_compounds, match_ions, match_isotopes]
        ),
        match_samples=match_samples,
        match_compounds=match_compounds,
        match_ions=match_ions,
        match_isotopes=match_isotopes,
    )

    resp = api_post(mascope_url, "samples/old", data=request_body)
    content = {} if not resp or resp.status_code != 200 else json.loads(resp.content)

    match_data = content.get("data", [])
    match_samples = content.get("batch_matches_info", {}).get("match_samples", [])
    match_compounds = content.get("batch_matches_info", {}).get("match_compounds", [])
    match_ions = content.get("batch_matches_info", {}).get("match_ions", [])
    match_isotopes = content.get("batch_matches_info", {}).get("match_isotopes", [])

    return {
        "sample_items_df": pd.DataFrame(match_data),
        "match_samples_df": pd.DataFrame(match_samples),
        "match_compounds_df": pd.DataFrame(match_compounds),
        "match_ions_df": pd.DataFrame(match_ions),
        "match_isotopes_df": pd.DataFrame(match_isotopes),
    }


def get_sample_items(mascope_url: str, sample_batch_id: str) -> list:
    """Get Mascope sample items from a URL from a sample batch

    :param mascope_url: Mascope URL
    :type mascope_url: str
    :param sample_batch_id: Sample batch ID
    :type sample_batch_id: str
    :return: List sample item tuples in the form (sample_item_name: str, sample_item: dict)
    :rtype: list
    """
    body = dict(
        sample_batch_id=sample_batch_id,
    )
    resp = api_post(mascope_url, "samples/old", data=body)
    content = None if not resp or resp.status_code != 200 else json.loads(resp.content)
    sample_items = content and content["data"] or []
    return [
        (sample_item["sample_item_name"], sample_item) for sample_item in sample_items
    ]


def get_sample_file_peaks(mascope_url: str, sample_file_id: str) -> dict:
    """Get peaks of given sample file

    :param mascope_url: Mascope server URL
    :type mascope_url: str
    :param sample_file_id: Sample file ID
    :type sample_file_id: str
    :return: Dictionary with keys:
        "mz": list of m/z of the peaks in sample file
        "intensity": peak intensity (area)
    :rtype: dict
    """
    resp = api_get(mascope_url, f"sample/files/{sample_file_id}/peaks")
    content = None if not resp or resp.status_code != 200 else json.loads(resp.content)
    return content["data"] if content is not None else None


def get_sample_file_peak_timeseries(
    mascope_url: str,
    sample_file_id: str,
    peak_mz: float,
    peak_mz_tolerance_ppm: float = None,
) -> dict:
    """Call /api/sample/files/{sample_file_id}/peaks/timeseries endpoint

    :param mascope_url: Mascope server URL
    :type mascope_url: str
    :param sample_file_id: Sample file ID
    :type sample_file_id: str
    :param peak_mz: m/z of the peak to request timeseries for
    :type peak_mz: float
    :param peak_mz_tolerance_ppm: m/z tolerance within which the peak
        should be compared to requested (ppm), defaults to None
    :type peak_mz_tolerance_ppm: float, optional
    :return: Dictionary with keys:
        "mz": m/z of the peak in sample file (None if no peak within tolerance)
        "intensity": peak height at time points (empty if no peak within tolerance)
        "time": time coordinates (empty if no peak within tolerance)
    :rtype: dict
    """
    body = (
        {
            "peak_mz": peak_mz,
            "peak_mz_tolerance_ppm": peak_mz_tolerance_ppm,
        }
        if peak_mz_tolerance_ppm is not None
        else {"peak_mz": peak_mz}
    )
    resp = api_post(
        mascope_url, f"sample/files/{sample_file_id}/peaks/timeseries", body
    )
    content = None if not resp or resp.status_code != 200 else json.loads(resp.content)
    return content["data"] if content is not None else None


def get_sample_file_spectrum(
    mascope_url: str,
    sample_file_id: str,
    t_min: float = None,
    t_max: float = None,
    mz_min: float = None,
    mz_max: float = None,
) -> dict:
    """
    Get the mass spectrum from a specified sample file within optional time and m/z ranges.

    :param mascope_url: Mascope server URL
    :type mascope_url: str
    :param sample_file_id: Sample file ID
    :type sample_file_id: str
    :param t_min: Start of the time range, defaults to None
    :type t_min: float, optional
    :param t_max: End of the time range, defaults to None
    :type t_max: float, optional
    :param mz_min: Start of the m/z range, defaults to None
    :type mz_min: float, optional
    :param mz_max: End of the m/z range, defaults to None
    :type mz_max: float, optional
    :return: Dictionary with keys: "total", optional "spectrum_count", "data" containing "mz" and "intensity" lists.
    :rtype: dict
    """
    # Construct the query parameters string based on provided arguments
    query_params = []
    if t_min is not None:
        query_params.append(f"t_min={t_min}")
    if t_max is not None:
        query_params.append(f"t_max={t_max}")
    if mz_min is not None:
        query_params.append(f"mz_min={mz_min}")
    if mz_max is not None:
        query_params.append(f"mz_max={mz_max}")
    query_params_str = "&".join(query_params)

    # Make the GET request to the API endpoint with query parameters
    resp = api_get(
        mascope_url, f"sample/files/{sample_file_id}/spectrum?{query_params_str}"
    )
    content = None if not resp or resp.status_code != 200 else json.loads(resp.content)
    return content["data"] if content is not None else None


def create_instrument_function(
    mascope_url: str,
    instrument: str,
    datetime_utc: str,
    peakshape: dict,
    resolution_function: list,
) -> dict:
    """
    Create a new instrument function record in the database.

    :param mascope_url: Base URL of the Mascope API
    :param instrument: Name of the instrument
    :param datetime_utc: UTC timestamp of the instrument function
    :param peakshape: Peak shape data containing 'x' and 'y' lists
    :param resolution_function: List containing resolution function parameters
    :return: The created instrument function details as received from the API response

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
    resp = api_post(mascope_url, "instrument_functions", data)

    # Handle the response
    if resp and resp.status_code == 201:
        # Successfully created the instrument function, extract 'data' from the response JSON
        response_json = resp.json()  # parse JSON response content
        # Return the 'data' part containing the instrument function details
        return response_json.get("data")

    # Handle errors or unsuccessful attempts
    error_message = (
        f"Failed to create instrument function. Status code: {resp.status_code}"
        if resp
        else "No response from server"
    )
    print(error_message)
    return {"error": error_message}


def get_sample_compound_matches(
    mascope_url: str,
    sample_item_id: str,
    target_compound_formula: str,
    target_compound_name: str = "Unknown Compound",
    filter_params: dict = None,
) -> dict:
    """
    Retrieves matches for compounds within a sample based on a target compound formula,
    applying specified filter parameters to filter the matches.

    :param mascope_url: Base URL of the Mascope API.
    :type mascope_url: str
    :param sample_item_id: Unique identifier of the sample item to analyze.
    :type sample_item_id: str
    :param target_compound_formula: Chemical formula of the target compound.
    :type target_compound_formula: str
    :param target_compound_name: The name of the target compound, defaults to "Unknown Compound"
    :type target_compound_name: str, optional
    :param filter_params: Parameters to filter the match results, affecting which matches are considered significant.
                          Should be a dictionary representing the FilterParams Pydantic model.
    :type filter_params: dict, optional
    TODO rename outer scope function def filter_params(ctx):
    :return: A dictionary containing the match data (compound->ions->isotopes)
    :rtype: dict

    Example of target compound and filter parameters data:
        "target_compound_formula": "C6H12N2O6",
        "target_compound_name": "Formic acid", # compound name is optional
        filter_params = {
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
    if filter_params is not None:
        body["filter_params"] = filter_params

    # Make the POST request for the specified sample
    resp = api_post(
        mascope_url, f"match/aggregate/sample/{sample_item_id}/compound", body
    )

    # Handle the successfull response
    if resp is not None and resp.status_code == 200:
        response_json = resp.json()
        return response_json.get("data")

    # Handle errors or unsuccessful attempts
    error_message = "No response from server"
    if resp is not None:
        error_content = resp.json()
        error_message = error_content.get(
            "error",
            f"Failed to retrieve compound matches. Status code: {resp.status_code}",
        )

    print(error_message)
    return {"error": error_message}
