#!/bin/pyton3

import os
import unittest
import asyncio
import time
import asynctest
import json

from systestlib import start_test_client_as_daemon, samples



class TestBaseTestClient(asynctest.TestCase):
    def setUp(self) -> None:
        self.client = start_test_client_as_daemon()
        return super().setUp()

    def tearDown(self) -> None:
        asyncio.run(self.client.join_requests())
        self.client.stop_client(f'{self.__class__.__name__} tearDown')
        return super().tearDown()

    def assert_requests_ok(self):
        asyncio.run(self.client.join_requests())
        if self.client.target_exception:
            self.fail(str(self.client.target_exception))


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


class TestSammpleManager(TestBaseTestClient):
    def setUp(self):
        super().setUp()
        # get list of available projects
        asyncio.run(
            self.client.emit_service_state(request_id='service_state')
        )
        self.assert_requests_ok()   # wait for service_state to be processed

    def assert_attrs(self, fname, attrs):
        with open(fname) as f:
            attrs_1 = json.dumps(json.load(f), sort_keys=True)
            attrs_2 = json.dumps(attrs, sort_keys=True)
            self.assertTrue(attrs_1, attrs_2)

    def test_projects(self):
        dirs = [d for d in os.listdir(self.client.projects_root) if 
                    os.path.isdir(os.path.join(self.client.projects_root, d))]
        self.assertTrue( sorted(self.client.projects) == sorted(dirs) )
        for p in self.client.projects.values():
            self.assert_attrs(os.path.join(p['path'], '.attrs'), p['attributes'])

    def test_project_selected(self):
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



    # def test_experiment_selected(self):
    #     pass

    # def test_save_project(self):
    #     print('AAAA', self.client.projects_root, self.client.projects)

        # asyncio.run(
        #     self.client.emit_client_notification(
        #         name='service_state',
        #         value={},
        #     )
        # )
        # asyncio.run(asyncio.sleep(3))

        # print('AAAA', datapool_path)
        # datapool = SamplePool(datapool_path)
        # project_name = 'LinuxProject'
        # project_path = os.path.join(datapool.projects_root, project_name)
        # orig_attrs = datapool._read_attributes(project_path)
        # print('AAAA', datapool.projects_root, orig_attrs)

        # def validator():
        #     pass

        # request_id = f"saveproject_{int(time.time())}"
        # asyncio.run(
        #     self.client.emit_client_notification(
        #         name='save_project',
        #         value={
        #             'request_id': request_id,
        #             'title': project_name,
        #             'attributes': request_id,
        #         },
        #     )
        # )

        # while timeout:
        #     validator()

    # def test_save_experiment(self):
    #     pass

    # def test_delete_experiment(self):
    #     pass

    # def test_delete_project(self):
    #     pass




if __name__ == '__main__':
   unittest.main()