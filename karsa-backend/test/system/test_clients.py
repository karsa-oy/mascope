#!/bin/pyton3

import os
import unittest
import asyncio
import time
import asynctest
import json
import datetime
import shutil
from ntpath import basename

from karsalib.util import parse_cmd_args
from systestlib import start_test_client_as_daemon, samples



class BaseTestClientCase(asynctest.TestCase):
    input_args = parse_cmd_args()

    @classmethod
    def setUpClass(cls):
        cls.client = start_test_client_as_daemon(**cls.input_args)

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls.client.join_requests())
        cls.client.stop_client(f'{cls.__name__} tearDownClass')

    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        asyncio.run(self.client.join_requests())
        self.client.reset()
        return super().tearDown()

    def assert_requests_ok(self, request_ids=None):
        asyncio.run(self.client.join_requests(request_ids))
        if self.client.target_exception:
            raise Exception(str(self.client.target_exception))


# @unittest.skip("TMP")
class TestValidateTesterCase(BaseTestClientCase):
    # Make sure test environment properly reacts to failures
    # BE CAREFUL: raised assertion kills main TestClient thread
    def test_validate_test_environment(self):
        fname = 'TofDaq_Data_2021.08.02_01h01m01s'
        max_exec_time = 3                                   # make it small for convenience
        t_range_max = samples[fname]['t_range_max'] + 1     # this limit will never be reached
        rq_suffix = self.client.set_test_params(fname, t_range_max=t_range_max, max_exec_time=max_exec_time)
        asyncio.run(
            self.client.emit_visualize_range(fname, request_id=f'zoom_{rq_suffix}'))
        with self.assertRaises(Exception) as ctx:
            self.assert_requests_ok()
        self.assertTrue('exceeded max execution time' in str(ctx.exception))


# @unittest.skip("TMP")
class TestVisualizerCase(BaseTestClientCase):
    def test_visualize_full_range(self):
        fname = 'TofDaq_Data_2021.08.02_01h01m01s'
        rq_suffix = self.client.set_test_params(fname)
        asyncio.run(self.client.emit_visualize_range(fname, request_id=f"fullrange_{rq_suffix}"))
        self.assert_requests_ok()


    def test_visualize_zoomed_range(self):
        fname = 'TofDaq_Data_2021.08.02_01h01m01s'
        max_exec_time = 10
        # TODO: batch size is 5.xx for the sample - what about other samples?
        t_range_01 = 21
        t_range=[5, t_range_01]
        mz_range=[100, 200]
        rq_suffix = self.client.set_test_params(fname, t_range_max=t_range_01-1, max_exec_time=max_exec_time)
        asyncio.run(
            self.client.emit_visualize_range(fname,
                                    request_id=f'zoom_{rq_suffix}',
                                    mz_range=mz_range,
                                    t_range=t_range)
        )
        self.assert_requests_ok()


    def test_visualize_two_ranges_sequentially(self):
        fname = 'TofDaq_Data_2021.08.02_01h01m01s'
        rq_suffix = self.client.set_test_params(fname)
        asyncio.run(self.client.emit_visualize_range(fname, request_id=f"fullrange_{rq_suffix}"))

        self.assert_requests_ok()     # wait for rq to complete and verify exceptions

        max_exec_time = 10
        t_range_01 = 16     # sample batch size is 5.xx
        t_range=[5, t_range_01]
        mz_range=[100, 200]
        rq_suffix = self.client.set_test_params(fname, t_range_max=t_range_01-1, max_exec_time=max_exec_time)
        asyncio.run(
            self.client.emit_visualize_range(fname,
                                    request_id=f'zoom_{rq_suffix}',
                                    mz_range=mz_range,
                                    t_range=t_range)
        )
        self.assert_requests_ok()


    def test_visualize_two_ranges_parallel(self):
        fname = 'TofDaq_Data_2021.08.02_01h01m01s'
        max_exec_time = 10
        rq_suffix = self.client.set_test_params(fname, max_exec_time=max_exec_time)
        asyncio.run(self.client.emit_visualize_range(fname, request_id=f"fullrange_{rq_suffix}"))

        max_exec_time = 10
        t_range_01 = 16
        t_range=[5, t_range_01]
        mz_range=[100, 200]
        rq_suffix = self.client.set_test_params(fname, t_range_max=t_range_01-1, max_exec_time=max_exec_time)
        asyncio.run(
            self.client.emit_visualize_range(fname,
                                    request_id=f'zoom_{rq_suffix}',
                                    mz_range=mz_range,
                                    t_range=t_range)
        )
        self.assert_requests_ok()


    @unittest.skip("TODO: fix data for both input files")
    def test_visualize_two_files_parallel(self):
        fname = 'file_1'
        rq_suffix = self.client.set_test_params(fname)
        asyncio.run(self.client.emit_visualize_range(fname, request_id=f"fullrange_{rq_suffix}"))
        fname = 'file_2'
        rq_suffix = self.client.set_test_params(fname)
        asyncio.run(self.client.emit_visualize_range(fname, request_id=f"fullrange_{rq_suffix}"))
        self.assert_requests_ok()


# @unittest.skip("TMP")
class TestSampleManagerCase(BaseTestClientCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # get list of available projects
        asyncio.run(
            cls.client.emit_service_state()
        )
        cls.assert_requests_ok(cls)   # wait for service_state to be processed

    def assert_attrs(self, fname, attrs):
        with open(fname) as f:
            attrs_1 = json.load(f)
            # if isinstance(attrs_1, list) and 'metadata_version_number' in attrs_1[-1]:
            #     attrs_1 = attrs_1[:-1]
            attrs_1 = json.dumps(attrs_1, sort_keys=True)
            attrs_2 = json.dumps(attrs, sort_keys=True)
            self.assertEqual(attrs_1, attrs_2)

    def test_01_projects(self):
        dirs = [d for d in os.listdir(self.client.projects_root) if 
                    os.path.isdir(os.path.join(self.client.projects_root, d))]
        self.assertTrue( sorted(self.client.projects) == sorted(dirs), f"{sorted(self.client.projects)} vs. {sorted(dirs)}" )
        for p in self.client.projects.values():
            self.assert_attrs(os.path.join(p['path'], '.attrs'), p['attributes'])

    def test_02_project_selected(self):
        pname = 'LinuxProject'
        asyncio.run(
            self.client.emit_project_selected(pname)
        )
        self.assert_requests_ok()
        # validate experiments of selected project
        pdir = os.path.join(self.client.projects_root, pname)
        dirs = [d for d in os.listdir(pdir) if 
                    os.path.isdir(os.path.join(pdir, d))]
        self.assertTrue( sorted(self.client.projects[pname]['experiments'].keys()) == sorted(dirs) )
        for e in self.client.projects[pname]['experiments'].values():
            self.assert_attrs(
                    os.path.join(self.client.projects[pname]['path'], e['title'], '.attrs'),
                    e['attributes'])
            self.assert_attrs(
                    os.path.join(self.client.projects[pname]['path'], e['title'], '.template'),
                    e['sample_attributes_template'])

    def test_03_experiment_selected(self):
        pname = 'LinuxProject'
        ename = 'Experiment_1'
        asyncio.run(
            self.client.emit_experiment_selected(pname, ename)
        )
        self.assert_requests_ok()
        # validate samples of selected experiment
        edir = os.path.join(self.client.projects_root, pname, ename)
        samples = [s for s in os.listdir(edir) if 
                    os.path.isdir(os.path.join(edir, s))]
        self.assertTrue( sorted(self.client.projects[pname]['experiments'][ename]['samples'].keys()) == sorted(samples) )
        for n, s in self.client.projects[pname]['experiments'][ename]['samples'].items():
            # validate attributes
            self.assert_attrs(
                    os.path.join(self.client.projects[pname]['path'], ename, n, '.attrs') ,
                    s['attributes'])
            # validate properties
            self.assert_attrs(
                    os.path.join(self.client.projects[pname]['path'], ename, n, '.props') ,
                    s['properties'])

    def test_04_save_project(self):
        pname = 'NewProject'
        attrs = 'NewProject attributes'
        pdir = os.path.join(self.client.projects_root, pname)
        # make sure no leftovers
        self.assertFalse(os.path.exists(pdir), pdir)
        asyncio.run(
            self.client.emit_save_project(pname, attrs)
        )
        self.assert_requests_ok()
        # validate project dir
        self.assertTrue(os.path.isdir(pdir))
        # validate attributes
        attr_path = os.path.join(pdir, '.attrs')
        self.assert_attrs(attr_path, attrs)

    def test_05_save_experiment(self):
        pname = 'NewProject'
        ename = 'NewExperiment'
        attrs = 'NewExperiment attributes'
        template = 'NewExperiment template'
        edir = os.path.join(self.client.projects_root, pname, ename)
        # make sure no leftovers
        self.assertFalse(os.path.exists(edir), edir)
        asyncio.run(
            self.client.emit_save_experiment(pname, ename, attrs, template)
        )
        self.assert_requests_ok()
        self.assertTrue(os.path.isdir(edir))
        # validate attrs and template
        p = os.path.join(edir, '.attrs')
        self.assert_attrs(p, attrs)
        p = os.path.join(edir, '.template')
        self.assert_attrs(p, template)

    def test_06_delete_experiment(self):
        pname = 'NewProject'
        ename = 'NewExperiment'
        edir = os.path.join(self.client.projects_root, pname, ename)
        self.assertTrue(os.path.isdir(edir), edir)
        asyncio.run(
            self.client.emit_delete_experiment(pname, ename)
        )
        self.assert_requests_ok()
        self.assertFalse(os.path.exists(edir), edir)

    def test_06_delete_project(self):
        pname = 'NewProject'
        pdir = os.path.join(self.client.projects_root, pname)
        self.assertTrue(os.path.isdir(pdir), pdir)
        asyncio.run(
            self.client.emit_delete_project(pname)
        )
        self.assert_requests_ok()
        self.assertFalse(os.path.exists(pdir), pdir)


# @unittest.skip("TMP")
class TestFileStreamerCase(BaseTestClientCase):
    @classmethod
    def setUpClass(cls):
        cls.input_args = {
            'url': 'localhost',
            'port': 5010,
            'ns': 'H5Data',
        }
        super().setUpClass()
        # declarative input data: win tests can not read it from OS correctly
        cls.data_collection_time = '2021.08.02'
        # datetime range with no samples
        cls.dt_range_empty = {'dt0': datetime.datetime(2021, 8, 1).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                              'dt1': datetime.datetime(2021, 8, 2).strftime('%Y-%m-%dT%H:%M:%S.%fZ')}
        # datetime range with samples;
        cls.dt_range_all = {'dt0': datetime.datetime(2021, 8, 1).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                           'dt1': datetime.datetime(2021, 8, 3).strftime('%Y-%m-%dT%H:%M:%S.%fZ')}
        cls.raw_samples = ['1-DataFile_2021.08.02-01h01m00s.h5',
                           '2-DataFile_2021.08.02-01h01m00s.h5',
                           '3-DataFile_2021.08.02-01h01m00s.h5',
                           '4-DataFile_2021.08.02-01h01m00s.h5']
        cls.data_collection_path = os.path.abspath(os.path.join(os.curdir, cls.client.instrument_name))
        # if os.path.isdir(cls.data_collection_path):
        #     shutil.rmtree(cls.data_collection_path)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if os.path.isdir(cls.data_collection_path):
            # the data_pool dir may be locked for some time
            time.sleep(3)
            shutil.rmtree(cls.data_collection_path)

    def test_01_import_raw_table_datetime_range_empty(self):
        asyncio.run(
            self.client.emit_import_raw_table_datetime_range(
                self.dt_range_empty,
                max_exec_time=3)
        )
        self.assert_requests_ok()
        self.assertEqual(self.client.raw_samples, [])

    def test_02_import_raw_table_datetime_range(self):
        # pre-defined DataPool structure is the test pre-requisite, since
        # file system operations can not be used for verification until
        # FileStreamer and unittests are run on different platforms (win/linux)
        # TODO: workaround - declarative sorted list of raw samples;
        # file list from os?
        asyncio.run(
            self.client.emit_import_raw_table_datetime_range(
                self.dt_range_all,
                max_exec_time=3)
        )
        self.assert_requests_ok()
        # self.raw_samples = os.listdir(self.client.raw_samples_dir)
        self.assertEqual(self.client.raw_samples, self.raw_samples)

    def test_03_raw_import_interrupted_with_status_checks(self):
        # send raw_import and check raw_import_status
        asyncio.run(
            self.client.emit_raw_import(
                self.client.raw_samples_data,
                request_id=None)    # don't track the request for completion
        )
        asyncio.run(asyncio.sleep(1))
        asyncio.run(
            self.client.emit_raw_import_status(
                request_id='raw_import_status',
                max_exec_time=3)
        )
        self.assert_requests_ok(['raw_import_status',])
        self.assertEqual(
            basename(self.client.raw_import_status_data['progress'][0]['filename']),
            self.raw_samples[0]
        )
        self.assertEqual(
            [basename(f['filename']) for f in self.client.raw_import_status_data['queue']['files']],
            self.raw_samples[1:]
        )
        # send stop_raw_import for sample in progress and check raw_import_status
        asyncio.run(
            self.client.emit_stop_raw_import()
        )
        # TODO: ugly workaround - so far no reliable way to trace stop_raw_import complete - just wait
        asyncio.run(asyncio.sleep(7))

        asyncio.run(
            self.client.emit_raw_import_status(
                request_id='raw_import_status',
                max_exec_time=3)
        )
        self.assert_requests_ok(['raw_import_status',])
        self.assertEqual(
            basename(self.client.raw_import_status_data['progress'][0]['filename']),
            self.raw_samples[1]
        )
        self.assertEqual(
            [basename(f['filename']) for f in self.client.raw_import_status_data['queue']['files']],
            self.raw_samples[2:]
        )
        # send stop_raw_import for the rest of samples and check raw_import_status
        asyncio.run(
            self.client.emit_stop_raw_import(self.client.raw_samples_data[1:])
        )
        # TODO: ugly workaround - so far no reliable way to trace stop_raw_import complete - just wait
        asyncio.run(asyncio.sleep(7))

        asyncio.run(
            self.client.emit_raw_import_status(
                request_id='raw_import_status',
                max_exec_time=3)
        )
        self.assert_requests_ok(['raw_import_status',])
        self.assertEqual(self.client.raw_import_status_data['progress'], [])
        self.assertEqual(self.client.raw_import_status_data['queue'], {})
        # only 2 target files were created, other two were cancelled
        if os.path.isdir(self.data_collection_path):
            # this check does not work, when running tests on windows
            names = os.listdir(os.path.join(self.data_collection_path, self.client.data_collection_date))
            names = sorted([n.replace(f'{self.client.instrument_name}_', '', 1) for n in names])
            self.assertEqual(names, self.raw_samples[0:2])

    def test_04_raw_import(self):
        asyncio.run(
            self.client.emit_raw_import(
                self.client.raw_samples_data[2:],
                max_exec_time=60)
        )
        self.assert_requests_ok()
        if os.path.isdir(self.data_collection_path):
            # this check does not work, when running tests on windows
            names = os.listdir(os.path.join(self.data_collection_path, self.client.data_collection_date))
            names = sorted([n.replace(f'{self.client.instrument_name}_', '', 1) for n in names])
            self.assertEqual(names, self.raw_samples)



if __name__ == '__main__':
   unittest.main()
