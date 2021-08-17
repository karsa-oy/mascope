#!/bin/pyton3

import unittest
import asyncio
import threading

import time
import asynctest

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


    # TODO: why on_loaded_data is called twice?
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


if __name__ == '__main__':
   unittest.main()