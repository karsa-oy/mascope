import getopt
import random
import string
import sys
import yaml

from datetime import datetime, timedelta


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

def get_client_notification_args(data):
    """
    Get shallow copy of client_notificaiton arguments
    ignoring 'name' and 'value' fields.
    """
    return copy_dict(data, ignore_keys=['name', 'value'])

def parse_cmd_args():
    """
    Parse command line arguments for the service application:
    ------------------------------
    --url : string
        Karsa Router url/ip  (default: localhost)
    --port : int
        Karsa Router port (default: 5010)
    """
    # Set defaults
    args_cmd = dict()
    args_file = dict()
    args_default = dict(url='localhost', port=5010, ns='/')
    # Parse cmd arguments
    opts, _ = getopt.getopt(sys.argv[1:], 'o:v',
                ['config=',
                 'n_jobs=',
                 'ns=',
                 'port=',
                 'data_pool_path=',
                 'data_pool_mask=',
                 'streamer_type=',
                 'url=',
                 ])
    for opt, arg in opts:
        assert opt[:2]=='--', f"Invalid argument {opt}"
        key = opt[2:]
        if key.lower() == 'config':
            # service config may be defined in yaml file
            with open(arg, 'r') as f:
                args_file = yaml.safe_load(f)
            continue
        args_cmd[key] = arg
    # command line options override the ones from the config file
    return {**args_default, **args_file, **args_cmd}