# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 14:34:17 2019

@author: Oskari Kausiala
"""

from datetime import datetime, timedelta


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
