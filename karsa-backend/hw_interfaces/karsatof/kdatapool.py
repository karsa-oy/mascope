# -*- coding: utf-8 -*-
"""Define classes to organize and access data files. 

Created on Mon Apr 15 15:39:30 2019
"""

import asyncio
import os
import fnmatch
import json
import shutil
import subprocess
import warnings
import xarray

import numpy as np
import pandas as pd

from datetime import datetime, timedelta
from time import sleep
from threading import Thread
from multiprocessing import Lock
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler

from .kevent import KEvent



class H5Pool():
    def __init__(self, data_path):
        """Initialize self

        Parameters
        ----------
        data_path : str
            Root data path
        """

        self.data_root = data_path
        self.pool = pd.DataFrame()

    async def scan_dir(self,
                       path=None,
                       fname_filter='*.h5'
                       ):
        """Scan directory for h5 files
        
        This function walks through the given path, trying to find data files
        matching the given filter.
        
        path : str
            Root path
        fname_filter : datetime.datetime
            String to match the filename with. The default is 'Data*.h5'.
        recursive : bool, optional
            Scan recursively. The default is False.

        """
        
        if path is None:
            path = self.data_root

        print("Scanning: %s" % str(path))

        self.pool = pd.DataFrame(index=[],
                                 data=[],
                                 columns=['filename',
                                          'datetime',
                                          'filesize',
                                          'path',
                                          ]
                                 )
        # Get directories in path
        try:
            dirnames = next( os.walk(path) )[1]
        except StopIteration:
            print("Done")
            return
        # Loop through directories in root, assumed to be named by date
        for dirname in dirnames:
            await asyncio.sleep(0)
            try:
                dir_date = datetime.strptime(dirname, '%Y.%m.%d')
            except ValueError:
                print("Skipped directory: %s due to invalid datetime format" %dirname)
                continue
            dir_path = os.path.join(path, dirname)
            # Loop through files inside
            dir_files = next( os.walk(dir_path) )[2]
            for filename in fnmatch.filter(dir_files, fname_filter):
                await asyncio.sleep(0)
                # Try to parse time from filename
                file_no_ext = os.path.splitext(filename)[0]
                try:
                    time_str = file_no_ext.split('_')[-1] # Separator _
                    file_time = datetime.strptime(time_str, '%Hh%Mm%Ss')
                except ValueError:
                    try:
                        time_str = file_no_ext.split('-')[-1] # Separator -
                        file_time = datetime.strptime(time_str, '%Hh%Mm%Ss')
                    except ValueError:
                        print("Skipped file: %s due to invalid datetime format" %filename)
                        continue
                file_datetime = dir_date + timedelta(hours=file_time.hour,
                                                     minutes=file_time.minute,
                                                     seconds=file_time.second
                                                     )
                # Append to pool
                rawfile = os.path.join(path, dirname, filename)

                size_bytes = os.stat(rawfile).st_size
                size_mb = round(2**-20 * size_bytes, 2)

                df_row = pd.DataFrame(
                                index=[filename],
                                data=[[
                                    filename,
                                    file_datetime,
                                    size_mb,
                                    dir_path
                                    ]],
                                columns=[
                                    'filename',
                                    'datetime',
                                    'filesize',
                                    'path'
                                    ]
                                )
                self.pool = self.pool.append(df_row)
                print(str(rawfile))
        self.pool = self.pool.sort_index()
        print("Done")

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


class DataPool():
    """DataPool structure

    Assuming folder structure as follows:

    -Projects
    --experiment0
    ---sample0
    ---sample1
    ---sample2
    --experiment1
    ---sample3
    ---sample4
    --experiment2
    ---sample0

    """
    def __init__(self, data_path, projects_path):
        """Initialize self

        Parameters
        ----------
        projects_path : str
            Path to "Projects". All directories beneath Projects
            are assumed to refered to a project, containing experiment
            directories
        """

        self.data_root = data_path
        self.projects_root = projects_path
        self.pool = {}

        # If given projects root does not exist, create
        if not os.path.isdir(projects_path):
            os.mkdir(projects_path)

        # Project directories in projects_path
        projects = next( os.walk(projects_path) )[1]
        for project in projects:
            self.pool.update({ project: {} })
            project_path = os.path.join(projects_path, project)
            # Experiment directories in current project directory
            project_experiments = next( os.walk(project_path) )[1]
            for experiment in project_experiments:
                # Update samples of current experiment
                self.update_experiment_samples(project, experiment)

    def _make_link(self, source_path, target_path):
        """Make symbolic link from directory to another

        Used for linking sample directories to experiments.

        TODO: Make OS independent

        Parameters
        ----------
        source_path : str
            Source directory path (sample)
        target_path : str
            Target directory path (experiment)
        """

        if not os.path.isdir(target_path):
            # TODO: Is this a safe way to do it? Windows dependent at least
            subprocess.check_call(
                        'mklink /J "%s" "%s"' % (target_path, source_path),
                        shell=True
                        )
            # Alternative way (requires elevated privileges)
            # os.symlink(source_path, target_path, target_is_directory=True)

    def _read_attributes(self, path):
        attr_path = os.path.join(path, '.attrs')
        if not os.path.exists(attr_path):
            return {}
        with open(attr_path, 'r') as f:
            attributes = json.load(f)
        return attributes

    def _write_attributes(self, path, attributes, overwrite=True):
        attr_path = os.path.join(path, '.attrs')
        if os.path.exists(attr_path) and not overwrite:
            raise ValueError("Attribute file %s exists already!" % attr_path)
        # Write attributes
        with open(attr_path, 'w') as f:
            json.dump(attributes, f, indent=4)
    
    def get_experiments(self, project):
        project_path = os.path.join(self.projects_root, project)
        experiment_titles = self.pool.get(project).keys()
        experiments = []
        for experiment in experiment_titles:
            experiment_path = os.path.join(project_path, experiment)
            experiment_attrs = self._read_attributes(experiment_path)
            experiments.append({'id': experiment,
                                'attributes': experiment_attrs
                                })
        return experiments

    def get_projects(self):
        project_titles = self.pool.keys()
        projects = []
        for project in project_titles:
            project_path = os.path.join(self.projects_root, project)
            project_attrs = self._read_attributes(project_path)
            projects.append({'id': project,
                             'attributes': project_attrs
                             })
        return projects

    def get_samples(self, project, experiment):
        if project is None and experiment is None:
            # All samples
            sample_titles = next( os.walk(self.data_root) )[1]
        else:
            # Samples in given project and experiment
            sample_titles = self.pool.get(project).get(experiment)
        samples = []
        for sample in sample_titles:
            sample_path = os.path.join(self.data_root, sample)
            sample_attrs = self._read_attributes(sample_path)
            if 'id' not in sample_attrs.keys():
                sample_attrs.update( {'id': sample} )
            samples.append({'id': sample,
                            'attributes': sample_attrs
                            })
        return samples

    def get_sample_table(self, project=None, experiment=None):
        samples = self.get_samples(project, experiment)
        sample_table_rows = [sample.get('attributes')
                             for sample in samples
                             ]
        sample_table_cols = []
        if len(sample_table_rows) > 0:
            attrs = sample_table_rows[0].keys() # TODO: Need to check for all unique keys?
            sample_table_cols = [
                        {'field': attr.lower(),
                         'label': attr.capitalize(),
                         }
                        for attr in attrs
                        ]
        return {'rows': sample_table_rows,
                'cols': sample_table_cols
                }

    def new_project(self, project, attributes):
        project_path = os.path.join(self.projects_root, project)
        # Make project directory
        if not os.path.isdir(project_path):
            os.mkdir(project_path)
        # Write attributes
        self._write_attributes(project_path, attributes)
        # Update self.pool
        self.pool.update({ project: {} })

    def new_experiment(self, project, experiment, attributes):
        experiment_path = os.path.join(self.projects_root, project, experiment)
        # Make experiment directory
        if not os.path.isdir(experiment_path):
            os.mkdir(experiment_path)
        # Write attributes
        self._write_attributes(experiment_path, attributes)
        # Update self.pool
        self.pool[project].update({ experiment: [] })

    def new_sample(self, project, experiment, sample, attributes):
        sample_data_path = os.path.join(
                                self.data_root,
                                sample
                                )
        sample_experiment_path = os.path.join(
                                self.projects_root,
                                project,
                                experiment,
                                sample
                                )
        # Check if sample exists
        if not os.path.isdir(sample_data_path):
            raise ValueError("Sample %s does not exist!" % sample_data_path)
        # If sample not yet part of the experiment, link it
        if not os.path.isdir(sample_experiment_path):
            self._make_link(sample_data_path, sample_experiment_path)
        # Write attributes
        self._write_attributes(sample_data_path, attributes)
        # Update self.pool
        self.update_experiment_samples(project, experiment)

    def update_experiment_samples(self, project, experiment):
        """Update samples under given experiment directory

        Parameters
        ----------
        project : str
            Project directory
        experiment : str
            Experiment directory
        """
        project_path = os.path.join(self.projects_root, project)
        experiment_path = os.path.join(project_path, experiment)
        # Sample directories in experiment directory
        sample_dirs = next( os.walk(experiment_path) )[1]
        experiment_samples = []
        for sample_dir in sample_dirs:
            experiment_samples.append(sample_dir)
        self.pool[project].update({ experiment: experiment_samples })



class KDataPool():
    """Class to scan a directory for data, and store the data with attributes
    in a pandas DataFrame.
    
    ...
    
    Attributes
    ----------
    path : str
        Directory path where the datapool points to
    timestamps_as_str : bool
        If True, store timestamps in str format, otherwise datetime
    pool : DataFrame
        Pandas DataFrame where the found data files are collected
    
    """
    
    def __init__(self,
                 path,
                 recursive=False,
                 fname_filter='Data*.h5',
                 timestamps_as_str=False,
                 diary=None):
        """Initialize self
        
        ...

        Parameters
        ----------
        path : str
            Directory path where the datapool points to
        recursive : bool, optional
            Scan recursively. The default is False.
        timestamps_as_str : bool, optional
            If True, store timestamps in str format, otherwise datetime.
            The default is False (datetime).
        diary : str, optional
            Path to diary text file. The default is None.
        """
        
        self.path = path
        self.timestamps_as_str = timestamps_as_str
        self.scan_directory(self.path,
                            recursive=recursive,
                            fname_filter=fname_filter,
                            diary=diary
                            )

    def scan_directory(self,
                       path,
                       fname_filter,
                       recursive=False,
                       diary=None):
        """Find raw files (in subfolders) of the given root directory
        
        This function walks through the given path, trying to find data files
        matching the given filter. For each found file, the 'append_pool'
        method is called.
        
        Parameters
        ----------
        path : str
            Path to scan
        fname_filter : str
            String to match the filename with. The default is 'Data*.h5'.
        recursive : bool, optional
            Scan recursively. The default is False.
        diary : str or None, optional
            Diary file name. The default is None.
        """
        
        self.path = path
        self.pool = pd.DataFrame(index=[],
                                 data=[],
                                 columns=['sample id',
                                          'description',
                                          'file',
                                          'start time',
                                          'end time',
                                          'length',
                                          'polarity',
                                          'note',
                                          'lock'
                                          ]
                                 )
        # Walk path and find files
        for root, dirnames, filenames in os.walk(path):
            for filename in fnmatch.filter(filenames, fname_filter):
                rawfile = os.path.join(root, filename)
                self.append_pool(rawfile)

            # zarr files are actually directories
            for filename in fnmatch.filter(dirnames, fname_filter):
                if '_tps' in filename:
                    continue #XXX: Hack to skip tps data files
                rawfile = os.path.join(root, filename)
                self.append_pool(rawfile)
            # scan on only root directory
            if recursive == False:
                break
        # Read measurement diary if given
        if diary is not None:
            self.read_diary(diary)
        
    def append_pool(self, rawfile, lock=Lock()):
        """Append data file to pool.
        
        This function tries to instantate KEvent for the given data file,
        in order to read attributes from the file. If it is succesful,
        a row will be added to the pool.

        Parameters
        ----------
        rawfile : str
            Full path of the data file
        lock : Lock, optional
            Lock object for the file, to be used for synchronizing
            file access. The default is to create a new Lock.
        """
        try:
            ke = KEvent(rawfile)
            if self.timestamps_as_str:
                dt0 = str(ke.dt0)
                dt1 = str(ke.dt1)
            else:
                dt0 = ke.dt0
                dt1 = ke.dt1
            df = pd.DataFrame( index=[os.path.basename(rawfile)],
                               data=[ np.array([ ke.sampleid,
                                                 ke.description,
                                                 ke.filename,
                                                 dt0,
                                                 dt1,
                                                 ke.length,
                                                 ke.polarity,
                                                 "",
                                                 lock]) ],
                               columns=['sample id',
                                        'description',
                                        'file',
                                        'start time',
                                        'end time',
                                        'length',
                                        'polarity',
                                        'note',
                                        'lock'] )
            self.pool = self.pool.append(df)
            
        except:
            # Maybe it is a zarr file
            # TODO: Properly
            try:
                ds = xarray.open_zarr(rawfile)
                if self.timestamps_as_str:
                    dt0 = ''
                    dt1 = ''
                else:
                    raise NotImplementedError
                df = pd.DataFrame(
                        index=[os.path.basename(rawfile)],
                        data=[ np.array([
                                    ds.attrs.get('sample_name', ''),
                                    ds.attrs.get('sample_description', ''),
                                    rawfile,
                                    dt0,
                                    dt1,
                                    0, #float(ds.data_array.time[-1]),
                                    '',
                                    "",
                                    lock
                                    ])
                               ],
                        columns=['sample id',
                                 'description',
                                 'file',
                                 'start time',
                                 'end time',
                                 'length',
                                 'polarity',
                                 'note',
                                 'lock'
                                 ]
                        )
                self.pool = self.pool.append(df)
            
            except Exception as e:
                print(e)
                print('Error: failed to read - %s' %rawfile)

            
    def read_diary(self, logfile):
        """Read free form text file and try to split it by dates
        
        This function finds lines in the diary of the form:
        '%d.%m.%Y\n' or
        '%d%m%Y\n'
        and splits the text accordingly. Finally it adds the nearest
        slice of diary text to rows in the pool.

        Parameters
        ----------
        logfile : str
            File path of the diary text file
        """
        
        dates = []
        notes = []
        # Split at date
        with open(logfile, 'r') as f:
            buf = []
            date = None
            for l in f:
                # Try to parse a date from current line
                try:
                    date = datetime.strptime(l, '%d.%m.%Y\n')
                except:
                    try:
                        date = datetime.strptime(l, '%d%m%Y\n')
                    except:
                        date = None
                        
                if date is not None:
                    dates.append(date)
                    if len(dates)==1:
                        buf = []
                        continue    
                    else:
                        note = "".join(buf)
                        try:
                            note = note.decode("utf-8")
                        except:
                            print(note)
                        notes.append(note)
                        buf = []
                buf.append(l)
            note = "".join(buf)
            note = note.decode("utf-8")
            notes.append(note)
        log = pd.DataFrame(index=dates, data=np.asarray(notes), columns=['note'])
        #self.pool['Note'] = ''
        for i, date in enumerate(log.index):
            if i < len(log)-1:
                next_date = log.index[i+1]
            else:
                next_date = date + timedelta(days=1)
                
            mask = np.logical_and( self.pool['start time'] >= date, 
                                   self.pool['start time'] < next_date)
            ind = mask.nonzero()[0]
            if len(ind) > 0:
                self.pool.loc[self.pool.index[ind], 'note'] = log.loc[date, 'note']




# class KWatchDog(Thread):
#     """Thread watching for file system changes in a set path including subfolders.
    
#     ...
    
#     Attributes
#     ----------
#     stop : bool
#         Shutdown flag
#     path : str
#         Path to watch
#     filewatch : KFileWatch
#         KFileWatch instance, defining the actions to be taken when change
#         is detected
#     observer : Observer
#         watchdog module Observer instance

#     """
    
#     def __init__(self,
#                  path,
#                  file_queue=None,
#                  datapool=None,
#                  dl_path=None):
#         """Initialize self
        
#         Watchdog is automatically started at initialization

#         Parameters
#         ----------
#         path : str
#             Path to watch
#         file_queue : Queue, optional
#             Passed to KFileWatch. The default is None.
#         datapool : KDataPool, optional
#             Passed to KFileWatch. The default is None.
#         dl_path : str, optional
#             Passed to KFileWatch. The default is None.
#         """
        
#         Thread.__init__(self)
#         self.stop = False
#         if os.path.exists(path):
#             self.path = path
#             self.start_watch(file_queue, datapool, dl_path)
#         else:
#             warnings.warn('Specified path does not exist. KWatchDog not started.')
#             self.observer = None
            
#     def start_watch(self, file_queue, datapool, dl_path):
#         """Start watchdog
        
#         Instantiate KFileWatch and watchdog.observers.Observer
#         to monitor the set path for file system changes.

#         Parameters
#         ----------
#         file_queue : Queue, optional
#             Passed to KFileWatch. The default is None.
#         datapool : KDataPool, optional
#             Passed to KFileWatch. The default is None.
#         dl_path : str, optional
#             Passed to KFileWatch. The default is None.
#         """
        
#         self.filewatch = KFileWatch(file_queue, datapool, dl_path)
#         self.observer = Observer()
#         self.observer.schedule(self.filewatch, self.path, recursive=True)
#         self.observer.start()
    
#     def run(self):
#         """Main loop"""
        
#         while not self.stop:
#             sleep(1)
#         if self.observer is not None:
#             self.observer.stop()
    
#     def stop_watch(self):
#         """Set shutdown flag"""
        
#         self.stop = True

# class KFileWatch(FileSystemEventHandler):
#     """Class to define the actions to be taken when KWatchDog detects changes
#     in the file system.
    
#     ...
    
#     Attributes
#     ----------
#     file_queue : Queue or None
#         Queue to put new file into
#     datapool : KDataPool or None
#         KDataPool to append new file into
#     dl_path : str or None
#         Path to copy the new file into
#     new_file : str or None
#         File name of the last new file after initialization
#     last_complete : str or None
#         File name of the second to last new file

#     """

#     def __init__(self, file_queue, datapool, dl_path):
#         """Initialize self

#         Parameters
#         ----------
#         file_queue : Queue
#             Queue to put new file into
#         datapool : KDataPool or None
#             KDataPool to append new file into
#         dl_path : str or None
#             Path to copy the new file into
#         """
        
#         FileSystemEventHandler.__init__(self)
#         self.file_queue = file_queue # Put new file to queue
#         self.datapool = datapool # Append new file to datapool
#         self.dl_path = dl_path # Directory to download the new file into
#         self.new_file = None
#         self.last_complete = None
        
#     def on_created(self, event):
#         """Action to be taken when new file is detected
        
#         It updates the attributes 'new_file' and 'last_complete',
#         copies the 'last_complete' file into 'dl_path' if defined,
#         puts the 'last_copied' file into 'file_queue' if defined and
#         lastly appends 'last_copied' to 'datapool' if defined.
        

#         Parameters
#         ----------
#         event : FileSystemEvent
#             Detected event in the file system
#         """
        
#         # File was created
#         if self.new_file is not None:
#             self.last_complete = self.new_file[:]
#         self.new_file = event.src_path
#         # Perform actions to the second to last file
#         #(TofDaq Recorder creates a file template beforehand in trigger mode)
#         if self.last_complete is not None:
#             if self.dl_path is not None:
#                 # Download
#                 if not os.path.isdir(self.dl_path):
#                     os.mkdir(self.dl_path)
#                 datedir = os.path.split(os.path.split(self.last_complete)[0])[1]
#                 dst_dir = os.path.join(self.dl_path, datedir)
#                 if not os.path.isdir(dst_dir):
#                     os.mkdir(dst_dir)
#                 fnam = os.path.basename(self.last_complete)
#                 dst = os.path.join(dst_dir, fnam)
#                 print('Downloading file: %s' %fnam)
#                 shutil.copy(self.last_complete, dst)
#                 last_copied = dst
#             if self.file_queue is not None:
#                 self.file_queue.put(last_copied)
#             if self.datapool is not None:
#                 self.datapool.append_pool(last_copied)