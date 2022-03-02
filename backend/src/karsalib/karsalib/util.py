import argparse
import fnmatch
import os
import random
import string
import yaml
import datetime_glob
from datetime import datetime, timedelta
from karsalib.struct import AttrDict


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
    CHARACTERS = (string.ascii_letters + string.digits + '-._~')
    return ''.join(random.sample(CHARACTERS, 15))

def get_client_notification_context(data):
    """
    Get shallow copy of client_notificaiton arguments
    ignoring 'name' and 'value' fields.
    """
    return copy_dict(data, ignore_keys=['name', 'value'])

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
    parser.add_argument("-n", "--ns", help="instrument namespace to connect", type=str, required=False)
    parser.add_argument("-c", "--config", help="path to yaml config file", type=str, required=False)
    parser.add_argument("-nj", "--n_jobs", help="number of job processors", type=int, required=False)
    parser.add_argument("-st", "--streamer_type", help="streamer type (H5/Raw)", type=str, required=False)
    parser.add_argument("-m", "--data_pool_mask", help="file mask to watch", type=str, required=False)
    parser.add_argument("-s", "--data_pool_path", help="source data pool path for streaming (before date dirs)", type=str, required=False)
    parser.add_argument("-t", "--target_data_pool_path", help="target data pool path for streaming (before date dirs)", type=str, required=False)
    parser.add_argument("-tr", "--transit", help="transit mode for streaming", action='store_true', required=False)

    default_args = dict(url='localhost', port=5010, ns='/')

    all_args = parser.parse_args()
    cmdline_args = {}
    for arg in vars(all_args):
        if vars(all_args)[arg] is None:
            continue
        cmdline_args[arg] = vars(all_args)[arg]
    file_args = {}
    if all_args.config:
        # service config may be defined in yaml file
        with open(all_args.config, 'r') as f:
            file_args = yaml.safe_load(f)
    return AttrDict(
        **{ **default_args,
            **file_args,
            **cmdline_args})

def parse_datetime_from_item_filename(filename):
    global FILENAME_DATETIME_PATTERNS
    for pattern in FILENAME_DATETIME_PATTERNS:
        matcher = datetime_glob.Matcher(pattern=pattern)
        dt = matcher.match(filename)
        if dt:
            # Parsed succesfully
            break
    return dt.as_datetime()

def parse_path_from_item_filename(item_filename):
    """Return path (relative to wdir) to sample data, based on its name

    Path is
        wdir/instrument/yyyy.mm.dd/sample_name

    Parameters
    ----------
    sample_name : str
        Sample name (format: instrument_*%Y.%m.%d*%Hh%Mm%Ss*)
    """

    def parse_subdir_from_datetime(datetime):
        date_dir = '%.4d.%.2d.%.2d' %(datetime.year,
                                      datetime.month,
                                      datetime.day
                                      )
        return date_dir

    # Instrument name
    instrument = item_filename.split('_')[0]
    # Parse datetime and convert to date subdirectory name (yyyy.mm.dd)
    item_datetime = parse_datetime_from_item_filename(item_filename)
    date_dir = parse_subdir_from_datetime(item_datetime)
    # Join to sample path relative to wdir
    return os.path.join(instrument, date_dir, item_filename)



# # TODO: UGLY WORKAROUND -- The old parse_cmd_args is left here for system testing,
# # since new implementation somehow conflicts with unittest framework in handling args.
# #
# import getopt, sys
# def parse_cmd_args():
#     """
#     Parse command line arguments for the service application:
#     ------------------------------
#     --url : string
#         Karsa Router url/ip  (default: localhost)
#     --port : int
#         Karsa Router port (default: 5010)
#     """
#     # Set defaults
#     args_cmd = dict()
#     args_file = dict()
#     args_default = dict(url='localhost', port=5010, ns='/')
#     # Parse cmd arguments
#     opts, _ = getopt.getopt(sys.argv[1:], 'o:v',
#                 ['config=',
#                  'n_jobs=',
#                  'ns=',
#                  'port=',
#                  'data_pool_path=',
#                  'data_pool_mask=',
#                  'streamer_type=',
#                  'target_data_pool_path=',
#                  'url=',
#                  ])
#     for opt, arg in opts:
#         assert opt[:2]=='--', f"Invalid argument {opt}"
#         key = opt[2:]
#         if key.lower() == 'config':
#             # service config may be defined in yaml file
#             with open(arg, 'r') as f:
#                 args_file = yaml.safe_load(f)
#             continue
#         args_cmd[key] = arg
#     # command line options override the ones from the config file
#     return {**args_default, **args_file, **args_cmd}

