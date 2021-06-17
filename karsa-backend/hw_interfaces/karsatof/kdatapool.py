# -*- coding: utf-8 -*-
"""Define classes to organize and access data files. 

Created on Mon Apr 15 15:39:30 2019
"""

import asyncio
import os
import fnmatch
import json
import subprocess

import numpy as np
import pandas as pd

import datetime_glob
from datetime import datetime, timedelta
from shutil import rmtree
from time import sleep
from multiprocessing import Lock

# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler

from .kevent import KEvent


METADATA_VERSION_NUMBER = '0.01'


FILENAME_DATETIME_PATTERNS = [
        '*%Y.%m.%d*%Hh%Mm%Ss*',
        '*%Y%m%d_%H%M_*',
        '*%Y%m%d_*',
        ]

def parse_path_from_sample_name(sample_name):
    """Return path (relative to wdir) to sample data, based on its name

    Path is
        wdir/instrument/yyyy.mm.dd/sample_name

    Parameters
    ----------
    sample_name : str
        Sample name (format: instrument_*%Y.%m.%d*%Hh%Mm%Ss*)
    """
    def parse_datetime_from_sample_name(filename):
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
    instrument = sample_name.split('_')[0]
    # Parse datetime and convert to date subdirectory name (yyyy.mm.dd)
    sample_datetime = parse_datetime_from_sample_name(sample_name)
    date_dir = parse_subdir_from_datetime(sample_datetime)
    # Join to sample path relative to wdir
    return os.path.join(instrument, date_dir, sample_name)




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


class RawPool():
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
                       fname_filter='*.raw'
                       ):
        """Scan directory for raw files
        
        This function walks through the given path, trying to find data files
        matching the given filter.
        
        path : str
            Root path
        fname_filter : datetime.datetime
            String to match the filename with. The default is '*.raw'.
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

        # Get list of all files
        try:
            files = next( os.walk(path) )[2]
        except StopIteration:
            # No files
            print("Done")
            return
        # Loop through files in root, assumed to be named by date
        for filename in fnmatch.filter(files, fname_filter):
            await asyncio.sleep(0)
            # Try to parse time from filename
            matcher = datetime_glob.Matcher(pattern='%Y%m%d %H%M *')
            file_datetime_match = matcher.match(filename)
            if not file_datetime_match:
                print("Skipped file: %s due to invalid datetime format" %filename)
                continue
            file_datetime = file_datetime_match.as_datetime()

            # Append to pool
            rawfile = os.path.join(path, filename)

            size_bytes = os.stat(rawfile).st_size
            size_mb = round(2**-20 * size_bytes, 2)

            df_row = pd.DataFrame(
                            index=[filename],
                            data=[[
                                filename,
                                file_datetime,
                                size_mb,
                                path
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


class SamplePool():
    """Sample hierarchy: Projects/Experiments/Samples

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
    def __init__(self, projects_path):
        """Initialize self

        Parameters
        ----------
        projects_path : str
            Path to "Projects". All directories beneath Projects
            are assumed to refered to a project, containing experiment
            directories
        """

        self.projects_root = os.path.abspath(projects_path)
        self.pool = {}

        # If given projects root does not exist, create
        if not os.path.isdir(self.projects_root):
            os.mkdir(self.projects_root)

        # Project directories in projects_path
        projects = next( os.walk(self.projects_root) )[1]
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
                'mklink /J "%s" "%s"' % (os.path.abspath(target_path), os.path.abspath(source_path)),
                shell=True
                )
            # Alternative way (requires elevated privileges)
            # os.symlink(source_path, target_path, target_is_directory=True)

    def _remove_link(self, path):
        try:
            os.remove(path)
        except Exception as e:
            print(e)

    def _read_attributes(self, path, prefix='', ext='.attrs'):
        attr_path = os.path.join(path, prefix + ext)
        if not os.path.exists(attr_path):
            print("SamplePool._read_attributes: File not found: %s" %attr_path)
            return {}
        with open(attr_path, 'r') as f:
            attributes = json.load(f)

        if isinstance(attributes, list):
            if 'metadata_version_number' in attributes[-1]:
                metadata_version_number = attributes.pop()

        return attributes

    def _write_sample_annotation(self, path, prefix, annotation, ext='.annts'):
        annotation.update({'metadata_version_number': METADATA_VERSION_NUMBER})

        file_path = os.path.join(path, prefix + ext)
        if not os.path.exists(file_path):
            # Annotations file does not yet exist, create
            with open(file_path, 'w') as f:
                json.dump([annotation], f, indent=4)
        else:
            # Append annotations file
            with open(file_path, 'r+') as f:
                annotations = json.load(f)
                annotations.append(annotation)
                f.seek(0)
                json.dump(annotations, f, indent=4)

    def _write_attributes(self, path, attributes, prefix='', ext='.attrs', overwrite=False):
        if isinstance(attributes, list):
            attributes.append({'metadata_version_number': METADATA_VERSION_NUMBER})
        elif isinstance(attributes, dict):
            attributes.update({'metadata_version_number': METADATA_VERSION_NUMBER})

        attr_path = os.path.join(path, prefix + ext)
        if os.path.exists(attr_path) and not overwrite:
            raise ValueError("Attribute file %s exists already!" % attr_path)
        # Write attributes
        with open(attr_path, 'w') as f:
            json.dump(attributes, f, indent=4)
    
    def annotate_sample(self, project, experiment, sample, annotation):
        sample_path = os.path.join(self.projects_root, project, experiment)
        self._write_sample_annotation(sample_path, sample, annotation)

    def delete_experiment(self, project, experiment):
        experiment_path = os.path.join(self.projects_root, project, experiment)
        rmtree(experiment_path, ignore_errors=False, onerror=None)
        self.pool.get(project).pop(experiment)

    def delete_project(self, project):
        project_path = os.path.join(self.projects_root, project)
        rmtree(project_path, ignore_errors=False, onerror=None)
        self.pool.pop(project)

    def delete_sample(self, project, experiment, sample):
        sample_link_path = os.path.join(
                                self.projects_root,
                                project,
                                experiment,
                                sample
                                )
        self._remove_link(sample_link_path)
        # Update self.pool
        self.update_experiment_samples(project, experiment)

    def edit_experiment(self, project, experiment, attributes):
        '''Edit experiment attributes'''
        experiment_path = os.path.join(self.projects_root, project, experiment)
        # Write new attributes
        self._write_attributes(experiment_path, attributes, overwrite=True)

    def edit_project(self, project, attributes):
        '''Edit experiment attributes'''
        project_path = os.path.join(self.projects_root, project)
        # Write new attributes
        self._write_attributes(project_path, attributes, overwrite=True)

    def edit_sample(self, project, experiment, sample, attributes, method):
        '''Edit sample attributes'''
        experiment_path = os.path.join(self.projects_root, project, experiment)
        # Write attributes
        self._write_attributes(experiment_path, attributes, prefix=sample, overwrite=True)
        # Write method
        self._write_attributes(experiment_path, method, prefix=sample, ext='.meth', overwrite=True)

    def get_experiments(self, project):
        project_path = os.path.join(self.projects_root, project)
        experiment_titles = self.pool.get(project).keys()
        experiments = []
        for experiment in experiment_titles:
            experiment_path = os.path.join(project_path, experiment)
            experiment_attrs = self._read_attributes(experiment_path)
            experiment_sample_attrs_template = self._read_attributes(
                                                            experiment_path,
                                                            ext='.template'
                                                            )
            experiments.append({
                    'title': experiment,
                    'project': project,
                    'attributes': experiment_attrs,
                    'sample_attributes_template': experiment_sample_attrs_template
                    })
        return experiments

    def get_projects(self):
        project_titles = self.pool.keys()
        projects = []
        for project in project_titles:
            project_path = os.path.join(self.projects_root, project)
            project_attrs = self._read_attributes(project_path)
            projects.append({'title': project,
                             'attributes': project_attrs
                             })
        return projects

    def get_samples(self, project, experiment):
        if project is None:
            # Should return all samples
            # TODO: Need to get samples from FileIO
            raise NotImplementedError
        elif experiment is None:
            # Samples in given project
            experiments = self.pool.get(project)
        else:
            # Samples in given project and experiment
            experiments = [experiment]
            
        samples = []
        for experiment in experiments:
            sample_ids = self.pool.get(project).get(experiment)
            for sample_id in sample_ids:
                # Read experiment-specific sample attributes
                experiment_path = os.path.join(self.projects_root,
                                               project,
                                               experiment
                                               )
                sample_exp_attrs = self._read_attributes(experiment_path,
                                                         prefix=sample_id
                                                         )
                # Read sample properties
                sample_path = os.path.join(experiment_path, sample_id)
                sample_props = self._read_attributes(sample_path)
                
                samples.append({'filename': sample_id,
                                'project': project,
                                'experiment': experiment,
                                'properties': sample_props,
                                'attributes': sample_exp_attrs,
                                })
        return samples

    def new_project(self, project, attributes):
        project_path = os.path.join(self.projects_root, project)
        # Make project directory
        if not os.path.isdir(project_path):
            os.mkdir(project_path)
        # Write attributes
        self._write_attributes(project_path, attributes)
        # Update self.pool
        self.pool.update({ project: {} })

    def new_experiment(self, project, experiment, attributes, sample_attributes_template):
        experiment_path = os.path.join(self.projects_root, project, experiment)
        # Make experiment directory
        if not os.path.isdir(experiment_path):
            os.mkdir(experiment_path)
        # Write attributes
        self._write_attributes(experiment_path, attributes)
        # Write sample attributes template
        self._write_attributes(experiment_path, 
                               sample_attributes_template,
                               ext='.template'
                               )
        # Update self.pool
        self.pool[project].update({ experiment: [] })

    def new_sample(self, project, experiment, sample, attributes, method):
        # Data path
        sample_data_path = parse_path_from_sample_name(sample)
        # Meta-data path
        experiment_path = os.path.join(self.projects_root, project, experiment)
        sample_experiment_path = os.path.join(experiment_path, sample)
        # Check if sample exists
        if not os.path.isdir(sample_data_path):
            raise ValueError("Sample %s does not exist!" % sample_data_path)
        # If sample not yet part of the experiment, link it
        if not os.path.isdir(sample_experiment_path):
            self._make_link(sample_data_path, sample_experiment_path)
        # Write attributes
        self._write_attributes(experiment_path, attributes, prefix=sample)
        # Write method
        self._write_attributes(experiment_path, method, prefix=sample, ext='.meth')
        # Update self.pool
        self.update_experiment_samples(project, experiment)

    def new_sample_placeholder(self, project, experiment, sample, attributes):
        # Meta-data path
        experiment_path = os.path.join(self.projects_root, project, experiment)
        sample_experiment_path = os.path.join(experiment_path, sample)
        dummy_link_target = sample_experiment_path
        self._make_link(dummy_link_target, sample_experiment_path)
        # Write attributes
        self._write_attributes(experiment_path, attributes, prefix=sample)
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