#!/bin/pyton3

import os
import unittest
import asyncio
import time
import asynctest
import json

from systestlib import start_test_client_as_daemon, samples



class TestBaseTestClient(asynctest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = start_test_client_as_daemon()

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls.client.join_requests())
        cls.client.stop_client(f'{cls.__name__} tearDownClass')

    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        asyncio.run(self.client.join_requests())
        return super().tearDown()

    def assert_requests_ok(self):
        asyncio.run(self.client.join_requests())
        if self.client.target_exception:
            self.fail(str(self.client.target_exception))



@unittest.skip("TEMP")
class TestVisualizer(TestBaseTestClient):
    # Make sure test environment properly reacts to failures
    def test_validate_test_environment(self):
        fname = 'TofDaq_Data_2021.08.02_18h53m56s'
        max_exec_time = 3                                   # make it small for convenience
        t_range_max = samples[fname]['t_range_max'] + 1     # this limit will never be reached
        rq_suffix = self.client.set_test_params(fname, t_range_max=t_range_max, max_exec_time=max_exec_time)
        asyncio.run(
            self.client.emit_visualize_range(fname, request_id=f'zoom_{rq_suffix}'))
        with self.assertRaises(AssertionError) as ctx:
            self.assert_requests_ok()
        self.assertTrue('exceeded max execution time' in str(ctx.exception))


    def test_visualize_full_range(self):
        fname = 'TofDaq_Data_2021.08.02_18h53m56s'
        rq_suffix = self.client.set_test_params(fname)
        asyncio.run(self.client.emit_visualize_range(fname, request_id=f"fullrange_{rq_suffix}"))
        self.assert_requests_ok()


    def test_visualize_zoomed_range(self):
        fname = 'TofDaq_Data_2021.08.02_18h53m56s'
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
        fname = 'TofDaq_Data_2021.08.02_18h53m56s'
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
        fname = 'TofDaq_Data_2021.08.02_18h53m56s'
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


class TestSampleManager(TestBaseTestClient):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # get list of available projects
        asyncio.run(
            cls.client.emit_service_state(request_id='service_state')
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
            self.client.emit_project_selected(pname, request_id='project_selected')
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
            self.client.emit_experiment_selected(pname, ename, request_id='experiment_selected')
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
            self.client.emit_save_project(pname, attrs, request_id='save_project')
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
            self.client.emit_save_experiment(pname, ename, attrs, template, request_id='save_experiment')
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
            self.client.emit_delete_experiment(pname, ename, request_id='delete_experiment')
        )
        self.assert_requests_ok()
        self.assertFalse(os.path.exists(edir), edir)

    def test_06_delete_project(self):
        pname = 'NewProject'
        pdir = os.path.join(self.client.projects_root, pname)
        self.assertTrue(os.path.isdir(pdir), pdir)
        asyncio.run(
            self.client.emit_delete_project(pname, request_id='delete_project')
        )
        self.assert_requests_ok()
        self.assertFalse(os.path.exists(pdir), pdir)



if __name__ == '__main__':
   unittest.main()