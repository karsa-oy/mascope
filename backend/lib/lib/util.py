import argparse
import fnmatch
import os
import random
import re
import string
from datetime import datetime, timedelta

import datetime_glob
import yaml

from .structs import AttrDict


def copy_dict(d, ignore_keys=[]):
    return {k: v for k, v in d.items() if k not in ignore_keys}


def ct_struct_to_dict(struct):
    """Convert ctypes struct to dict

    Parameters
    ----------
    struct : Structure
        ctypes Structure to convert

    Returns
    -------
    dict
        Dictionary with the 'struct' contents
    """
    result = {}
    for field, _ in struct._fields_:
        value = getattr(struct, field)
        # if the type is not a primitive and it evaluates to False ...
        if (type(value) not in [int, float, bool]) and not bool(value):
            # it's a null pointer
            value = None
        elif hasattr(value, "_length_") and hasattr(value, "_type_"):
            # Probably an array
            value = list(value)
        elif hasattr(value, "_fields_"):
            # Probably another struct
            value = ct_struct_to_dict(value)
        elif type(value) == bytes:
            value = value.decode()
        result[field] = value
    return result


def filetime2datetime(timestamp):
    """Function to convert timestamp in FILETIME format to datetime

    Parameters
    ----------
    timestamp : int64
        Number of 100-nanosecond intervals since January 1, 1601

    Returns
    -------
    datetime
        Input timestamp converted to datetime format
    """

    _FILETIME_null_date = datetime(1601, 1, 1, 0, 0, 0)
    return _FILETIME_null_date + timedelta(microseconds=timestamp / 10)


def generate_unique_key():
    """Generate a 15 character long random string
    Returns
    -------
    str
        Random string with 15 characters
    """
    CHARACTERS = string.ascii_letters + string.digits + "-._~"
    return "".join(random.sample(CHARACTERS, 15))


def get_client_notification_context(data):
    """
    Get shallow copy of client_notificaiton arguments
    ignoring 'name' and 'value' fields.
    """
    return copy_dict(data, ignore_keys=["name", "value"])


def timestamp_from_filename(filename):
    FILENAME_DATETIME_PATTERNS = [
        "*%Y.%m.%d*%Hh%Mm%Ss*",
        "*%Y%m%d_%H%M_*",
        "*%Y%m%d*%H%M*",
    ]

    for pattern in FILENAME_DATETIME_PATTERNS:
        matcher = datetime_glob.Matcher(pattern=pattern)
        dt = matcher.match(filename)
        if dt:
            # Parsed succesfully
            break
    if not dt:
        raise ValueError(f"Could not parse timestamp from filename: {filename}")
    return dt.as_datetime()


def parse_path_from_item_filename(item_filename, base_path=""):
    """Return path (relative to wdir) to sample data, based on its name

    Path is
        wdir/instrument/yyyy.mm.dd/sample_name

    Parameters
    ----------
    sample_name : str
        Sample name (format: instrument_*%Y.%m.%d*%Hh%Mm%Ss*)
    """

    def parse_subdir_from_datetime(datetime):
        date_dir = "%.4d.%.2d.%.2d" % (datetime.year, datetime.month, datetime.day)
        return date_dir

    # Instrument name
    instrument = item_filename.split("_")[0]
    # Parse datetime and convert to date subdirectory name (yyyy.mm.dd)
    item_datetime = timestamp_from_filename(item_filename)
    date_dir = parse_subdir_from_datetime(item_datetime)
    # Join to sample path relative to wdir
    full_path = os.path.join(base_path, instrument, date_dir, item_filename)
    return full_path


def recursive_walk(dir_path, *file_masks):
    print("walking", dir_path)
    res = []
    cur_dir, dirs, files = next(os.walk(dir_path))
    for file_mask in file_masks:
        fs = fnmatch.filter(files, file_mask)
        fs = map(lambda fname: os.path.join(cur_dir, fname), fs)
        res.extend(fs)
    for d in dirs:
        fs = recursive_walk(os.path.join(cur_dir, d), *file_masks)
        res.extend(fs)
    return res


def parse_cmd_args():
    """
    Parse command line arguments for the service application:
    ------------------------------
    Return AttrDict.
    Default argument values: see default_args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", help="backend url", type=str, required=False)
    parser.add_argument("-p", "--port", help="backend port", type=int, required=False)
    parser.add_argument(
        "-n", "--ns", help="instrument namespace to connect", type=str, required=False
    )
    parser.add_argument(
        "-c", "--config", help="path to yaml config file", type=str, required=False
    )
    parser.add_argument(
        "-i", "--instrument", help="instrument name", type=str, required=False
    )
    parser.add_argument(
        "-m", "--data_pool_mask", help="file mask to watch", type=str, required=False
    )
    parser.add_argument(
        "-nj", "--n_jobs", help="number of job processors", type=int, required=False
    )
    parser.add_argument(
        "-s",
        "--data_pool_path",
        help="source data pool path for streaming (before date dirs)",
        type=str,
        required=False,
    )
    parser.add_argument(
        "-st",
        "--streamer_type",
        help="streamer type (H5/Raw)",
        type=str,
        required=False,
    )
    parser.add_argument(
        "-t",
        "--target_data_pool_path",
        help="target data pool path for streaming (before date dirs)",
        type=str,
        required=False,
    )
    parser.add_argument(
        "-tr",
        "--transit",
        help="transit mode for streaming",
        action="store_true",
        required=False,
    )

    all_args = parser.parse_args()
    cmdline_args = {}
    for arg in vars(all_args):
        if vars(all_args)[arg] is None:
            continue
        cmdline_args[arg] = vars(all_args)[arg]
    file_args = {}
    if all_args.config:
        # service config may be defined in yaml file
        with open(all_args.config, "r") as f:
            file_args = yaml.safe_load(f)
    return AttrDict(**{**file_args, **cmdline_args})


def to_snake_case(value):
    if isinstance(value, str):
        string = value
        if len(string) > 0:
            string = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", string)
            string = re.sub("([a-z0-9])([A-Z])", r"\1_\2", string).lower()
        return string
    else:
        return value


def to_camel_case(value):
    if isinstance(value, str):
        string = value
        words = string.split("_")
        return words[0] + "".join(word.title() for word in words[1:])
    else:
        return value


def map_keys(obj, func):
    if isinstance(obj, list):
        result = []
        for i in range(len(obj)):
            result.append(map_keys(obj[i], func))
    elif isinstance(obj, dict):
        result = dict()
        for key in obj.keys():
            result[func(key)] = map_keys(obj[key], func)
    else:
        result = obj
    return result


def map_to_snake_case(obj):
    return map_keys(obj, to_snake_case)


def map_to_camel_case(obj):
    return map_keys(obj, to_camel_case)
