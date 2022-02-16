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
    """Sample hierarchy: Projects/Experiments/Samples

    Assuming folder structure as follows:

    projects_path:

    -project0
    --experiment0
    ---sample0
    ---sample1
    ---sample2
    --experiment1
    ---sample3
    ---sample4
    --experiment2
    ---sample0
    -project1
    ...

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
        self.df = pd.DataFrame()

        # If given projects root does not exist, create
        if not os.path.isdir(self.projects_root):
            os.mkdir(self.projects_root)

        self._init_pool_dict()
        self._init_pool_dataframe()


    def _get_sample_df(self, project=None, experiment=None, sample=None):
        if project is None:
            # Return empty dataframe
            return pd.Series({
                        'properties': {},
                        'attributes': {},
                        'method': {},
                        'annotations': {},
                        })

        sample_metadata = self.get_sample_metadata(project,
                                                   experiment,
                                                   sample
                                                   )
        sample_df = pd.Series(
                    {**sample_metadata,
                    #  'peak list': pd.DataFrame.from_dict(
                    #                 {'mz': [],
                    #                  'intensity': [],
                    #                  'peak id': [],
                    #                  }
                    #                 ),
                    #  'target list': pd.DataFrame.from_dict(
                    #                 {'target id': [],
                    #                  'concentration': [],
                    #                  }    
                    #                 ),
                     }
                    )
        return sample_df

    def _init_pool_dict(self):
        self.pool = {}
        # Project directories in projects_path
        projects = next( os.walk(self.projects_root) )[1]
        # Loop through project directories
        for project in projects:
            self.pool.update({ project: {} })
            project_path = os.path.join(self.projects_root, project)
            # Experiment directories in current project directory
            project_experiments = next( os.walk(project_path) )[1]
            # Loop through experiment directories inside current project
            for experiment in project_experiments:
                experiment_path = os.path.join(project_path, experiment)
                # Sample directories in experiment directory
                experiment_samples = next( os.walk(experiment_path) )[1]
                self.pool[project].update({ experiment: experiment_samples })

    def _init_pool_dataframe(self):
        index = []
        data = []
        # Project directories in projects_path
        projects = next( os.walk(self.projects_root) )[1]
        # Loop through project directories
        for project in projects:
            project_path = os.path.join(self.projects_root, project)
            # Experiment directories in current project directory
            project_experiments = next( os.walk(project_path) )[1]
            if project_experiments:
                # Loop through experiment directories inside current project
                for experiment in project_experiments:
                    experiment_path = os.path.join(project_path, experiment)
                    # Sample directories in experiment directory
                    sample_dirs = next( os.walk(experiment_path) )[1]
                    if sample_dirs:
                        # Loop through samples inside current experiment
                        for sample in sample_dirs:
                            sample_df = self._get_sample_df(project, experiment, sample)
                            index.append((project, experiment, sample))
                            data.append(sample_df)
                    else:
                        index.append((project, experiment, None))
                        data.append(self._get_sample_df())
            else:
                index.append((project, None, None))
                data.append(self._get_sample_df())
        
        multi_index = pd.MultiIndex.from_tuples(index,
                                                names=('project', 'experiment', 'sample')
                                                )
        self.df = pd.DataFrame(index=multi_index,
                               data=data
                               )

    def _make_link(self, source_path, target_path, overwrite=False):
        """Make symbolic link from directory to another

        Used for linking sample directories to experiments.

        Parameters
        ----------
        source_path : str
            Source directory path (sample)
        target_path : str
            Target directory path (experiment)
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


    @staticmethod
    def _wait_for_dir(path, timeout=None):
        # sometimes it takes longer for sample directory to be created:
        CREATE_NEW_SAMPLE_TIMEOUT = 10.
        timeout = timeout or CREATE_NEW_SAMPLE_TIMEOUT
        t_start = time.time()
        while time.time() - t_start < CREATE_NEW_SAMPLE_TIMEOUT:
            if os.path.isdir(path):
                break
            time.sleep(.1)

    @classmethod
    def _read_attributes(cls, path, prefix='', ext='.attrs'):
        cls._wait_for_dir(path)
        attr_path = os.path.join(path, prefix + ext)
        with open(attr_path, 'r') as f:
            attributes = json.load(f)
        return attributes

    def _write_sample_annotation(self, path, annotation, prefix='', ext='.annts'):
        self._wait_for_dir(path)
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
        self._wait_for_dir(path)
        attr_path = os.path.join(path, prefix + ext)
        if os.path.exists(attr_path) and not overwrite:
            raise ValueError("Attribute file %s exists already!" % attr_path)
        # Write attributes
        with open(attr_path, 'w') as f:
            json.dump(attributes, f, indent=4)
    
    def annotate_sample(self, project, experiment, sample, annotation):
        sample_link = os.path.join(self.projects_root, project, experiment, sample)
        self._write_sample_annotation(sample_link, annotation)
        # TODO: Update df

    def delete_experiment(self, project, experiment):
        experiment_path = os.path.join(self.projects_root, project, experiment)
        rmtree(experiment_path, ignore_errors=False, onerror=None)
        self.pool[project].pop(experiment)
        self.df = self.df.drop((project, experiment))

    def delete_project(self, project):
        project_path = os.path.join(self.projects_root, project)
        rmtree(project_path, ignore_errors=False, onerror=None)
        self.pool.pop(project)
        self.df = self.df.drop(project, level=0)

    def delete_sample(self, project, experiment, sample):
        sample_link_path = os.path.join(
                                self.projects_root,
                                project,
                                experiment,
                                sample
                                )
        self._remove_link(sample_link_path)
        # Update self.pool
        self.pool[project][experiment].remove(sample)
        self.df = self.df.drop((project, experiment, sample))

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

    def edit_sample(self, project, experiment, sample, attributes=None, method=None):
        '''Edit sample attributes'''
        sample_link = os.path.join(self.projects_root, project, experiment, sample)
        if attributes is not None:
            # Write attributes
            self._write_attributes(sample_link, attributes, ext='.attrs', overwrite=True)
            self.df.loc[project, experiment, sample].attributes = attributes
        if method is not None:
            # Write method
            self._write_attributes(sample_link, method, ext='.meth', overwrite=True)
            self.df.loc[project, experiment, sample].method = method        

    def get_experiment_metadata(self, project, experiment):
        project_path = os.path.join(self.projects_root, project)
        experiment_path = os.path.join(project_path, experiment)
        experiment_attrs = self._read_attributes(experiment_path)
        experiment_sample_attrs_template = self._read_attributes(
                                                        experiment_path,
                                                        ext='.template'
                                                        )
        return {'attributes': experiment_attrs,
                'sample_attributes_template': experiment_sample_attrs_template
                }

    def get_experiments(self, project):
        experiment_titles = self.pool.get(project).keys()
        experiments = []
        for experiment in experiment_titles:
            experiment_metadata = self.get_experiment_metadata(project, experiment)
            experiments.append({
                    'title': experiment,
                    'project': project,
                    **experiment_metadata
                    })
        return experiments

    def get_project_metadata(self, project):
        project_path = os.path.join(self.projects_root, project)
        project_attrs = self._read_attributes(project_path)
        return {'attributes': project_attrs,
                }

    def get_projects(self):
        project_titles = self.pool.keys()
        projects = []
        for project in project_titles:
            project_path = os.path.join(self.projects_root, project)
            project_metadata = self.get_project_metadata(project)
            projects.append({'title': project,
                             'path': project_path,
                             **project_metadata,
                             })
        return projects

    def get_sample_metadata(self, project, experiment, sample):
        sample_link = os.path.join(self.projects_root, project, experiment, sample)
        self._wait_for_dir(sample_link)
        error_msg = None
        sample_ext = {}
        n_tries = 3
        while n_tries:
            try:
                for ext in ['.attrs', '.props', '.meth', '.annts']:
                    sample_ext[ext] = self._read_attributes(sample_link, ext=ext)
                break
            except Exception as e:
                error_msg = f"[{this_func_name()}] Error reading {sample}/{ext}: {e.__class__.__name__}({str(e)})"
                n_tries -= 1
                time.sleep(.1)
        if not n_tries:
            print(error_msg)
        return {
                    # 'filename': sample,
                    # 'project': project,
                    # 'experiment': experiment,
                    'properties': sample_ext.get('.props', {}),
                    'attributes': sample_ext.get('.attrs', {}),
                    'method': sample_ext.get('.meth', {}),
                    'annotations': sample_ext.get('.annts', {}),
                }

    def get_samples(self, project=None, experiment=None):
        # Clean NaNs
        flat_df = self.df.reset_index()
        flat_df_clean = flat_df.loc[flat_df['sample'].dropna().index]
        df = flat_df_clean.set_index('sample')

        if project is None:
            # Return all samples
            return df
        elif experiment is None:
            # Samples in given project
            try:
                return df.loc[df.project==project]
            except KeyError:
                return pd.DataFrame()
        else:
            # Samples in given project and experiment
            try:
                return df.loc[(df.project==project) & (df.experiment==experiment)]
            except KeyError:
                return pd.DataFrame()

    def new_project(self, project, attributes):
        project_path = os.path.join(self.projects_root, project)
        # Make project directory
        if not os.path.isdir(project_path):
            os.mkdir(project_path)
        # Write attributes
        self._write_attributes(project_path, attributes)
        # Update self.pool
        self.pool.update({ project: {} })
        new_row_index = pd.MultiIndex.from_tuples(
                                [(project, None, None)],
                                names=('project', 'experiment', 'sample')
                                )
        self.df = self.df.append(pd.DataFrame(index=new_row_index,
                                              data=[]
                                              )
                                 )

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

        new_row_index = pd.MultiIndex.from_tuples([(project, experiment, None)])
        self.df = self.df.append(pd.DataFrame(index=new_row_index,
                                              data=[]
                                              )
                                 )
        # In case of previously empty project, remove NaN index
        flat_df = self.df.reset_index()
        flat_df_clean = flat_df.loc[(flat_df.project!=project) |
                                    (flat_df['experiment'].notna())
                                    ]
        self.df = flat_df_clean.set_index(self.df.index.names)

    def new_sample(self, project, experiment, sample, attributes=[], method={}, annotations=[], placeholder=False):
        # Meta-data path
        experiment_path = os.path.join(self.projects_root, project, experiment)
        sample_experiment_path = os.path.join(experiment_path, sample)
        # Data path
        if placeholder:
            # Creating a placeholder for a sample, make dummy sample dir
            sample_data_path = sample_experiment_path
            os.mkdir(sample_data_path)
        else:
            # Actual sample, link to data file
            sample_data_path = parse_path_from_sample_name(sample)
            # Make link from experiment directory to data file -
            # the link can be made even to non-existing yet source dir
            self._make_link(sample_data_path, sample_experiment_path, overwrite=True)

        self._wait_for_dir(sample_data_path)
        # Write attributes
        try:
            for spec, ext in [(attributes, '.attrs'), (method, '.meth'), (annotations, '.annts')]:
                self._write_attributes(sample_data_path, spec, ext=ext, overwrite=True)
        except Exception as e:
            raise Exception(f"[{this_func_name()}] Error writing {sample}/{ext}: {e.__class__.__name__}({str(e)})")
        # add new sample to target pool
        self.pool[project][experiment].append(sample)
        
        new_row_index = pd.MultiIndex.from_tuples([(project, experiment, sample)])
        new_row_data = self._get_sample_df(project, experiment, sample)
        self.df = self.df.append(pd.DataFrame(index=new_row_index,
                                              data=[new_row_data]
                                              )
                                 )
        # In case of previously empty experiment, remove NaN index
        flat_df = self.df.reset_index()
        # flat_df_clean = flat_df.loc[flat_df['sample'].dropna().index]
        flat_df_clean = flat_df.loc[(flat_df.project!=project) |
                                    (flat_df.experiment!=experiment) |
                                    (flat_df['sample'].notna())
                                    ]
        self.df = flat_df_clean.set_index(self.df.index.names)


# class ZarrPool(H5Pool):
#     async def scan_dir(self,
#                        path=None,
#                        ):
#         """Scan directory for samples
        
#         This function walks through the given path, trying to find data files
#         matching the given filter.
        
#         path : str
#             Root path
#         fname_filter : datetime.datetime
#             String to match the filename with. The default is 'Data*.h5'.
#         recursive : bool, optional
#             Scan recursively. The default is False.

#         """
        
#         path = path or self.pool_attrs.get('path', '.')
#         dir_filters = ['*.raw', '*.h5']

#         print("Scanning: %s" % str(path))
#         if not os.path.isdir(path):
#             raise Exception(f"{path} missing of invalid")

#         self.pool = pd.DataFrame(index=[],
#                                  data=[],
#                                  columns=['filename',
#                                           'properties',
#                                           'attributes',
#                                           'method',
#                                           'annotations',
#                                           'datetime',
#                                           ]
#                                  )
#         samples = []
#         try:
#             samples = recursive_dir_walk(path, *dir_filters)
#         except StopIteration:
#             pass
#         for s in samples:
#             self.add_file(s)
#             print(' ', s)
#         print("Done")

#     def add_file(self, filename):
#         full_file_path = parse_path_from_sample_name(filename)
#         # Try to parse time from filename
#         patterns = ['*_%Y%m%d %H%M *',
#                     '*_%Y%m%d_%H%M_*',
#                     '*_%Y.%m.%d*%Hh%Mm%Ss*'
#                     ]
#         for pattern in patterns:
#             matcher = datetime_glob.Matcher(pattern=pattern)
#             file_datetime_match = matcher.match(filename)
#             if file_datetime_match:
#                 break
#         if not file_datetime_match:
#             print("Skipped file: %s due to invalid datetime format" %filename)
#             return
#         # Append to pool
#         file_datetime = file_datetime_match.as_datetime()
#         sample_metadata = self.get_sample_metadata(full_file_path)
#         df_row = pd.DataFrame(
#                         index=[filename],
#                         data=[[
#                             filename,
#                             sample_metadata.get('properties', {}),
#                             sample_metadata.get('attributes', {}),
#                             sample_metadata.get('method', {}),
#                             sample_metadata.get('annotations', {}),
#                             file_datetime,
#                             ]],
#                             columns=['filename',
#                                     'properties',
#                                     'attributes',
#                                     'method',
#                                     'annotations',
#                                     'datetime',
#                                     ]
#                         )
#         self.pool = self.pool.append(df_row).sort_index()

#     def get_sample_metadata(self, filepath):
#         sample_ext = {}
        
#         for ext in ['.attrs', '.props', '.meth', '.annts']:
#             try:
#                 sample_ext[ext] = SampleCatalog._read_attributes(filepath, ext=ext)
#             except Exception as e:
#                 print(e)
#         return {
#                     'properties': sample_ext.get('.props', {}),
#                     'attributes': sample_ext.get('.attrs', []),
#                     'method': sample_ext.get('.meth', []),
#                     'annotations': sample_ext.get('.annts', []),
#                 }
