# -*- coding: utf-8 -*-
"""Define classes to organize and access data files. 

Created on Mon Apr 15 15:39:30 2019
"""

import os
import re
from datetime import datetime, timedelta
from ntpath import basename, dirname

import datetime_glob
import pandas as pd

from .logger import NO_LOGGING_DEFAULT, parent_func_name
from .util import recursive_walk

METADATA_VERSION_NUMBER = "0.01"


class SamplePool:
    def log(self, *arg):
        if not NO_LOGGING_DEFAULT:
            print(f"[{self.__class__.__name__}.{parent_func_name()}]", *arg)

    def __init__(self, pool_attrs={}):
        """Initialize self

        Parameters
        ----------
        pool_attrs : dict
            Root data path, file masks to watch...
        """

        self.pool_attrs = pool_attrs
        self.pool = pd.DataFrame()

    async def scan_dir(self, path=None, fname_filter=None):
        """Scan directory for samples

        This function walks through the given path, trying to find data files
        matching the given filter.

        path : str
            Root path
        fname_filter : datetime.datetime
            String to match the filename with. The default is 'Data*.h5'.
        recursive : bool, optional
            Scan recursively. The default is False.
        """

        path = path or self.pool_attrs.get("path", ".")
        fname_filter = fname_filter or self.pool_attrs["mask"]

        self.log("Scanning: %s" % str(path))
        if not os.path.isdir(path):
            raise Exception(f"{path} missing of invalid")

        self.pool = pd.DataFrame(
            index=[],
            data=[],
            columns=[
                "filename",
                "datetime",
                "filesize",
                "path",
            ],
        )
        samples = []
        try:
            samples = recursive_walk(path, fname_filter)
        except StopIteration:
            pass
        for s in samples:
            self.add_file(s)
        print("Done")

    def datetime_from_filename(self, filename):
        pass

    def add_file(self, full_file_path):
        filename = basename(full_file_path)
        path = dirname(full_file_path)
        if filename in self.pool.filename:
            self.log("skip existing", full_file_path)
            return
        try:
            file_datetime = self.datetime_from_filename(filename)
        except Exception as e:
            self.log(f"skip {filename} : {str(e)}")
            return
        size_bytes = os.stat(full_file_path).st_size
        size_mb = round(2**-20 * size_bytes, 2)
        df_row = pd.DataFrame(
            index=[filename],
            data=[
                [
                    filename,
                    file_datetime,
                    size_mb,
                    path,
                ]
            ],
            columns=["filename", "datetime", "filesize", "path"],
        )
        self.pool = pd.concat([self.pool, df_row]).sort_index()
        self.log(filename)

    def remove_file(self, full_file_path):
        filename = basename(full_file_path)
        self.pool = self.pool.drop(filename)

    async def get_datetime_range(
        self, start_datetime=datetime(1970, 1, 1), end_datetime=datetime.now()
    ):
        """[summary]

        Parameters
        ----------
        start_date : datetime.datetime
            Start date
        end_date : datetime.datetime
            End date

        Returns
        -------
        [type]
            [description]
        """

        sub_pool = self.pool[
            (self.pool["datetime"] >= start_datetime)
            & (self.pool["datetime"] <= end_datetime)
        ].copy()

        sub_pool["datetime"] = sub_pool["datetime"].astype(str)

        sample_table = {
            "rows": list(sub_pool.to_dict("index").values()),
            "cols": [
                {
                    "field": col.lower(),
                    "label": col.capitalize(),
                }
                for col in sub_pool.columns
            ],
        }

        return sample_table


class H5Pool(SamplePool):
    def datetime_from_filename(self, filename):
        def get_h5_date_time(fname):
            dt_regex = r".*(\d{4}).(\d{2}).(\d{2}).(\d{2}).(\d{2}).(\d{2}).*"
            dt = re.findall(dt_regex, fname)[0]
            return datetime.strptime(".".join(dt[:3]), "%Y.%m.%d"), datetime.strptime(
                ".".join(dt[3:]), "%H.%M.%S"
            )

        try:
            file_date, file_time = get_h5_date_time(filename)
        except IndexError:
            raise Exception("invalid datetime format")
        return file_date + timedelta(
            hours=file_time.hour, minutes=file_time.minute, seconds=file_time.second
        )


class RawPool(SamplePool):
    def datetime_from_filename(self, filename):
        patterns = ["%Y%m%d %H%M *", "%Y%m%d_%H%M_*"]
        file_datetime_match = None
        for pattern in patterns:
            matcher = datetime_glob.Matcher(pattern=pattern)
            file_datetime_match = matcher.match(filename)
            if file_datetime_match:
                break
        if not file_datetime_match:
            raise Exception("invalid datetime format")
        try:
            return file_datetime_match.as_datetime()
        except Exception as e:
            raise Exception(f"{e.__class__.__name__}({str(e)})")
