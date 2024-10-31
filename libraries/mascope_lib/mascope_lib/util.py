import fnmatch
import os
import re

import datetime_glob

from mascope_lib.runtime import lib_runtime


FILENAME_DATETIME_PATTERNS = [
    "*%Y.%m.%d*%Hh%Mm%Ss*",
    "*%Y%m%d_%H%M_*",
    "*%Y%m%d%H%M%S*",
    "*%Y%m%d*%H%M%S*",
    "*%Y%m%d*%H%M*",
    "*%Y%m%d*",
]


def convert_datetime_pattern_to_regex(patterns) -> list:
    """Convert datetime_glob patterns to regex

    :param patterns: datetime_glob patterns
    :type patterns: list
    :return: Regex-compatible patterns
    :rtype: list
    """
    # map patterns
    strftime_to_regex = {
        "%Y": r"\d{4}",  # Year with century as a decimal number.
        "%m": r"\d{2}",  # Month as a zero-padded decimal number.
        "%d": r"\d{2}",  # Day of the month as a zero-padded decimal number.
        "%H": r"\d{2}",  # Hour (24-hour clock) as a zero-padded decimal number.
        "%M": r"\d{2}",  # Minute as a zero-padded decimal number.
        "%S": r"\d{2}",  # Second as a zero-padded decimal number.
        "*": r".*",  # Wildcard for any sequence of characters
        "h": "h",  # Literal characters
        "s": "s",
    }

    regex_patterns = []
    for pattern in patterns:
        regex_pattern = pattern

        # Replace each strftime directive or wildcard with the appropriate regex pattern
        for strftime, regex in strftime_to_regex.items():
            regex_pattern = regex_pattern.replace(strftime, regex)

        # Remove wildcard from borders
        regex_pattern = regex_pattern.strip(".*")

        regex_patterns.append(regex_pattern)
    return regex_patterns


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


def timestamp_from_filename(filename):
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
    lib_runtime.logger.info(f"walking {dir_path}")
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


def beautify_func_name(func_name: str, max_words: int = None) -> str:
    """
    Beautify a function name by replacing underscores with spaces.
    Optionally, limit the number of words used in the beautified name.

    :param func_name: The function name to beautify.
    :type func_name: str
    :param max_words: Maximum number of words to include in the beautified name.
    :type max_words: int, optional
    :return: The beautified function name.
    :rtype: str
    """
    if not isinstance(func_name, str):
        raise ValueError("Function name must be a string.")

    # Replace underscores with spaces and capitalize the first letter
    words = func_name.replace("_", " ").split()
    beautified_name = " ".join(words[:max_words]) if max_words else " ".join(words)

    return beautified_name


def norm(name: str, lower: bool = False) -> str:
    """
    Normalize a string by stripping leading and trailing spaces and converting to lowercase if specified.

    :param name: The string to normalize.
    :param lower: Whether to convert the string to lowercase. Defaults to False.
    :return: The normalized string.
    :rtype: str
    """
    if lower:
        name = name.lower()
    return " ".join(name.strip().split())


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
