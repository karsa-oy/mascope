# -*- coding: utf-8 -*-
"""Define classes to organize and access data files. 

Created on Mon Apr 15 15:39:30 2019
"""

import asyncio
import os
from ntpath import dirname, basename
import sys
import fnmatch
import json
import subprocess
import re
import time
from karsalib.util import recursive_walk, recursive_dir_walk
from karsalib.logging import (
                NO_DATA_LOGGING_DEFAULT,
                NO_LOGGING_DEFAULT,
                this_func_name,
                parent_func_name
                )

import numpy as np
import pandas as pd

import datetime_glob
from datetime import datetime, timedelta
from shutil import rmtree



METADATA_VERSION_NUMBER = '0.01'


FILENAME_DATETIME_PATTERNS = [
        '*%Y.%m.%d*%Hh%Mm%Ss*',
        '*%Y%m%d_%H%M_*',
        '*%Y%m%d_*',
        ]

def parse_path_from_item_filename(item_filename):
    """Return path (relative to wdir) to sample data, based on its name

    Path is
        wdir/instrument/yyyy.mm.dd/sample_name

    Parameters
    ----------
    sample_name : str
        Sample name (format: instrument_*%Y.%m.%d*%Hh%Mm%Ss*)
    """
    def parse_datetime_from_item_filename(filename):
        global FILENAME_DATETIME_PATTERNS
        for pattern in FILENAME_DATETIME_PATTERNS:
            matcher = datetime_glob.Matcher(pattern=pattern)
            dt = matcher.match(filename)
            if dt:
                # Parsed succesfully
                break
        if dt is None:
            return datetime.now()
        return dt.as_datetime()

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


class SamplePool():
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

    async def scan_dir(self,
                       path=None,
                       fname_filter=None
                       ):
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
        
        path = path or self.pool_attrs.get('path', '.')
        fname_filter = fname_filter or self.pool_attrs['mask']

        self.log("Scanning: %s" % str(path))
        if not os.path.isdir(path):
            raise Exception(f"{path} missing of invalid")

        self.pool = pd.DataFrame(index=[],
                                 data=[],
                                 columns=['filename',
                                          'datetime',
                                          'filesize',
                                          'path',
                                          ]
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
            self.log('skip existing', full_file_path)
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
                        data=[[
                            filename,
                            file_datetime,
                            size_mb,
                            path,
                            ]],
                        columns=[
                            'filename',
                            'datetime',
                            'filesize',
                            'path'
                            ]
                        )
        self.pool = self.pool.append(df_row).sort_index()
        self.log(filename)

    def remove_file(self, full_file_path):
        filename = basename(full_file_path)
        self.pool = self.pool.drop(filename)

    async def get_datetime_range(self,
                                 start_datetime=datetime(1970, 1, 1),
                                 end_datetime=datetime.now()
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

        sub_pool = self.pool[(self.pool['datetime'] >= start_datetime) &
                             (self.pool['datetime'] <= end_datetime)
                             ].copy()

        sub_pool['datetime'] = sub_pool['datetime'].astype(str)

        sample_table = {'rows': list( sub_pool.to_dict('index').values() ),
                        'cols': [ {'field': col.lower(),
                                   'label': col.capitalize(),
                                   }
                                  for col in sub_pool.columns ]
                        }
        
        return sample_table


class H5Pool(SamplePool):
    def datetime_from_filename(self, filename):
        def get_h5_date_time(fname):
            dt_regex = r'.*(\d{4}).(\d{2}).(\d{2}).(\d{2}).(\d{2}).(\d{2}).*'
            dt = re.findall(dt_regex, fname)[0]
            return  datetime.strptime('.'.join(dt[:3]), '%Y.%m.%d'), \
                    datetime.strptime('.'.join(dt[3:]), '%H.%M.%S')
        try:
            file_date, file_time = get_h5_date_time(filename)
        except IndexError:
            raise Exception("invalid datetime format")
        return file_date + timedelta(hours=file_time.hour,
                                    minutes=file_time.minute,
                                    seconds=file_time.second
                                    )


class RawPool(SamplePool):
    def datetime_from_filename(self, filename):
        patterns = ['%Y%m%d %H%M *', '%Y%m%d_%H%M_*']
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


class SampleCatalog():
    """Sample hierarchy: Workspaces/SampleBatches/SampleItems

    Assuming folder structure as follows:

        workspaces_path
            /workspace_id
                /item_batch_id
                    /item_item_id

    """
    def __init__(self, workspaces_path):
        """Initialize self

        Parameters
        ----------
        workspaces_path : str
            Path to the "workspaces" directory, containing workspace
            directories, which in turn contain item batch folders
            containing item item folders.
        """

        self.workspaces_root = os.path.abspath(workspaces_path)
        self.pool = {}
        self.df = pd.DataFrame()

        # If given workspaces root does not exist, create
        if not os.path.isdir(self.workspaces_root):
            os.mkdir(self.workspaces_root)

        self._init_pool_dict()
        self._init_pool_dataframe()

    def _init_pool_dict(self):
        self.pool = {}
        # Project directories in workspaces_path
        workspace_ids = next(os.walk(self.workspaces_root))[1]
        # Loop through workspace directories
        for workspace_id in workspace_ids:
            self.pool.update({ workspace_id: {} })
            workspace_path = self.get_workspace_path(workspace_id)
            # Experiment directories in current workspace directory
            batch_ids = next( os.walk(workspace_path) )[1]
            # Loop through batch directories inside current workspace
            for batch_id in batch_ids:
                batch_path = self.get_batch_path(workspace_id, batch_id)
                # Sample directories in batch directory
                item_ids = next( os.walk(batch_path) )[1]
                self.pool[workspace_id].update({ batch_id: item_ids })

    def _init_pool_dataframe(self):
        index = []
        data = []
        # Project directories in workspaces_path
        workspace_ids = next( os.walk(self.workspaces_root) )[1]
        # Loop through workspace directories
        for workspace_id in workspace_ids:
            workspace_path = self.get_workspace_path(workspace_id)
            # Experiment directories in current workspace directory
            batch_ids = next( os.walk(workspace_path) )[1]
            if batch_ids:
                # Loop through batch directories inside current workspace
                for batch_id in batch_ids:
                    batch_path = self.get_batch_path(workspace_id, batch_id)
                    # Sample directories in batch directory
                    item_dirs = next( os.walk(batch_path) )[1]
                    if item_dirs:
                        # Loop through items inside current batch
                        for item_id in item_dirs:
                            item_df = self._get_item_df(workspace_id, batch_id, item_id)
                            index.append((workspace_id, batch_id, item_id))
                            data.append(item_df)
                    else:
                        index.append((workspace_id, batch_id, None))
                        data.append(self._get_item_df())
            else:
                index.append((workspace_id, None, None))
                data.append(self._get_item_df())
        
        multi_index = pd.MultiIndex.from_tuples(index,
                                                names=('workspace_id', 'batch_id', 'item_id')
                                                )
        self.df = pd.DataFrame(index=multi_index,
                               data=data
                               )

    # helpers

    def _get_item_df(self, workspace_id=None, batch_id=None, item_id=None):
        if workspace_id is None:
            # Return empty dataframe
            return pd.Series({
                        'properties': {},
                        'attributes': {},
                        })

        item = self.get_item(workspace_id, batch_id, item_id)
        item_df = pd.Series({**item})

        return item_df

    @staticmethod
    def _wait_for_dir(path, timeout=None):
        # sometimes it takes longer for item directory to be created:
        CREATE_NEW_SAMPLE_TIMEOUT = 10.
        timeout = timeout or CREATE_NEW_SAMPLE_TIMEOUT
        t_start = time.time()
        while time.time() - t_start < CREATE_NEW_SAMPLE_TIMEOUT:
            if os.path.isdir(path):
                break
            time.sleep(.1)

    # links

    def _make_link(self, source_path, target_path, overwrite=False):
        """Make symbolic link from directory to another

        Used for linking item directories to batches.

        Parameters
        ----------
        source_path : str
            Source directory path (item)
        target_path : str
            Target directory path (batch)
        """

        if overwrite and os.path.exists(target_path):
            self._remove_link(target_path)
        if not os.path.exists(target_path):
            if 'win' in sys.platform:
                # TODO: Junctions/links are incompatible bw win/linux - switch to urls in .attr files
                subprocess.check_call(
                    'mklink /J "%s" "%s"' % (os.path.abspath(target_path), os.path.abspath(source_path)),
                    shell=True
                    )
                # Alternative way (requires elevated privileges)
                # os.symlink(source_path, target_path, target_is_directory=True)
            else:
                os.symlink(os.path.realpath(source_path), os.path.realpath(target_path))
        else:
            raise Exception(f"{target_path} exists")

    def _remove_link(self, path):
        try:
            os.remove(path)
        except Exception as e:
            print(e)

    # attributes

    @classmethod
    def _read_attributes(cls, path, prefix='', ext='.attrs'):
        cls._wait_for_dir(path)
        attr_path = os.path.join(path, prefix + ext)
        with open(attr_path, 'r') as f:
            attributes = json.load(f)
        return attributes

    def _write_attributes(self, path, attributes, prefix='', ext='.attrs', overwrite=False):
        self._wait_for_dir(path)
        attr_path = os.path.join(path, prefix + ext)
        if os.path.exists(attr_path) and not overwrite:
            raise ValueError("Attribute file %s exists already!" % attr_path)
        # Write attributes
        with open(attr_path, 'w') as f:
            json.dump(attributes, f, indent=4)
    
    # workspaces

    def get_workspace_path(self, workspace_id):
        return os.path.join(self.workspaces_root, workspace_id)

    def get_workspace(self, workspace_id):
        workspace_path = self.get_workspace_path(workspace_id)
        return self._read_attributes(workspace_path)

    def get_workspaces(self):
        workspace_ids = self.pool.keys()
        workspaces = []
        for workspace_id in workspace_ids:
            workspace = self.get_workspace(workspace_id)
            workspaces.append(workspace)
        return workspaces

    def new_workspace(self, workspace_id, attributes):
        workspace_path = self.get_workspace_path(workspace_id)
        # Make workspace directory
        if not os.path.isdir(workspace_path):
            os.mkdir(workspace_path)
        # Write attributes
        self._write_attributes(workspace_path, attributes)
        # Update self.pool
        self.pool.update({ workspace_id: {} })
        new_row_index = pd.MultiIndex.from_tuples(
                                [(workspace_id, None, None)],
                                names=('workspace_id', 'batch_id', 'item_id')
                                )
        self.df = self.df.append(pd.DataFrame(index=new_row_index,
                                              data=[]
                                              )
                                 )

    def edit_workspace(self, workspace_id, attributes):
        '''Edit batch attributes'''
        workspace_path = self.get_workspace_path(workspace_id)
        # Write new attributes
        self._write_attributes(workspace_path, attributes, overwrite=True)

    def delete_workspace(self, workspace_id):
        workspace_path = self.get_workspace_path(workspace_id)
        rmtree(workspace_path, ignore_errors=False, onerror=None)
        self.pool.pop(workspace_id)
        self.df = self.df.drop(workspace_id, level=0)

    # batches

    def get_batch_path(self, workspace_id, batch_id):
        workspace_path = self.get_workspace_path(workspace_id)
        return os.path.join(workspace_path, batch_id)

    def get_batch(self, workspace_id, batch_id):
        batch_path = self.get_batch_path(workspace_id, batch_id)
        return self._read_attributes(batch_path)

    def get_batches(self, workspace_id):
        batch_ids = self.pool.get(workspace_id).keys()
        batches = []
        for batch_id in batch_ids:
            batches.append(self.get_batch(workspace_id, batch_id))
        return batches

    def new_batch(self, workspace_id, batch_id, attributes):
        batch_path = self.get_batch_path(workspace_id, batch_id)
        # Make batch directory
        if not os.path.isdir(batch_path):
            os.mkdir(batch_path)
        # Write attributes
        self._write_attributes(batch_path, attributes)
        # Update self.pool
        self.pool[workspace_id].update({ batch_id: [] })

        new_row_index = pd.MultiIndex.from_tuples([(workspace_id, batch_id, None)])
        self.df = self.df.append(pd.DataFrame(index=new_row_index,
                                              data=[]
                                              )
                                 )
        # In case of previously empty workspace, remove NaN index
        flat_df = self.df.reset_index()
        flat_df_clean = flat_df.loc[(flat_df.workspace_id!=workspace_id) |
                                    (flat_df['batch'].notna())
                                    ]
        self.df = flat_df_clean.set_index(self.df.index.names)

    def edit_batch(self, workspace_id, batch_id, attributes):
        '''Edit batch attributes'''
        batch_path = os.path.join(self.workspaces_root, workspace, batch)
        # Write new attributes
        self._write_attributes(batch_path, attributes, overwrite=True)

    def delete_batch(self, workspace_id, batch_id):
        batch_path = self.get_batch_path(workspace_id, batch_id)
        rmtree(batch_path, ignore_errors=False, onerror=None)
        self.pool[workspace_id].pop(batch_id)
        self.df = self.df.drop((workspace_id, batch_id))

    # items

    def get_item_link(self, workspace_id, batch_id, item_id):
        return os.path.join(self.workspaces_root, workspace_id, batch_id, item_id)

    def get_item(self, workspace_id, batch_id, item_id):
        item_link = self.get_item_link(workspace_id, batch_id, item_id)
        self._wait_for_dir(item_link)
        error_msg = None
        item_data = {}
        n_tries = 3
        while n_tries:
            try:
                for ext in ['.attrs', '.props']:
                    item_data[ext] = self._read_attributes(item_path, ext=ext)
                break
            except Exception as e:
                error_msg = f"[{this_func_name()}] Error reading {item_id}/{ext}: {e.__class__.__name__}({str(e)})"
                n_tries -= 1
                time.sleep(.1)
        if not n_tries:
            print(error_msg)
        return {
                    **item_data.get('.attrs', {}),
                    'properties': item_data.get('.props', {}),
                }


    def get_items(self, workspace_id=None, batch_id=None):
        # Clean NaNs
        df = self.df.reset_index()
        df.loc[:, 'filename'] = df['item_id']
        df.rename(columns={
            'workspace_id': 'workspaceId',
            'batch_id': 'batchId',
            'item_id': 'id'
        }, inplace=True)

        if workspace_id is None:
            # all items
            return df.to_dict('records')
        elif batch_id is None:
            # items in given workspace
            try:
                filtered_df = df.loc[df.workspace_id==workspace_id]
                return filtered_df.to_dict('records')
            except KeyError:
                return None
        else:
            # items in given workspace and batch
            try:
                filtered_df = df.loc[(df.workspace_id==workspace_id) & (df.batch_id==batch_id)]
                return filtered_df.to_dict('records')
            except KeyError:
                return None

    def new_item(self, workspace_id, batch_id, item_id, attributes=[], placeholder=False):
        item_link = self.get_item_link(workspace_id, batch_id, item_id)
        # Data path
        if placeholder:
            # Creating a placeholder for a item, make dummy item dir
            item_path = item_link
            os.mkdir(item_path)
        else:
            # Actual item, link to data file
            item_path = parse_path_from_item_filename(filename)
            # Make link from batch directory to data file -
            # the link can be made even to non-existing yet source dir
            self._make_link(item_path, item_link, overwrite=True)

        self._wait_for_dir(item_path)
        # Write attributes
        try:
            self._write_attributes(item_data_path, attributes, ext='.attrs', overwrite=True)
        except Exception as e:
            raise Exception(f"[{this_func_name()}] Error writing {item_id}/{ext}: {e.__class__.__name__}({str(e)})")
        # add new item to target pool
        self.pool[workspace_id][batch_id].append(item_id)
        
        new_row_index = pd.MultiIndex.from_tuples([(workspace_id, batch_id, item_id)])
        new_row_data = self._get_item_df(workspace_id, batch_id, item_id)
        self.df = self.df.append(pd.DataFrame(index=new_row_index,
                                              data=[new_row_data]
                                              )
                                 )
        # In case of previously empty batch, remove NaN index
        flat_df = self.df.reset_index()
        # flat_df_clean = flat_df.loc[flat_df['item'].dropna().index]
        flat_df_clean = flat_df.loc[(flat_df.workspace_id!=workspace_id) |
                                    (flat_df.batch_id!=batch_id) |
                                    (flat_df['item_id'].notna())
                                    ]
        self.df = flat_df_clean.set_index(self.df.index.names)


    def edit_item(self, workspace_id, batch_id, item_id, attributes=None):
        '''Edit item attributes'''
        item_link = self.get_item_link(workspace_id, batch_id, item_id)
        if attributes is not None:
            # Write attributes
            self._write_attributes(item_link, attributes, ext='.attrs', overwrite=True)
            self.df.loc[workspace_id, batch_id, item_id].attributes = attributes
    
    def delete_item(self, workspace_id, batch_id, item_id):
        item_link = self.get_item_link(workspace_id, batch_id, item_id)
        self._remove_link(item_link)
        # Update self.pool
        self.pool[workspace_id][batch_id].remove(item_id)
        self.df = self.df.drop((workspace_id, batch_id, item_id))
