#!/bin/pyton3

import unittest
import asyncio
import threading

import time
import asynctest

from systestlib import start_test_client_as_daemon


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


    # TODO: why on_loaded_data is called twice?
    def test_visualize_full_range(self):
        fname = 'TofDaq_Data_2021.07.30_small'
        rq_suffix = self.client.set_test_params(fname)
        asyncio.run(self.client.emit_visualize_range(fname, request_id=f"fullrange_{rq_suffix}"))
        self.assert_requests_ok()


    @unittest.skip("NotImplemented: data format is different for zoomed on_loaded_data")
    def test_visualize_zoomed_range(self):
        # TODO: fix handlers for a separate use and together with visualize_full_range
        fname = 'TofDaq_Data_2021.07.30_small'
        max_exec_time = 30
        t_range_max = 10
        t_range=[5, t_range_max]
        mz_range=[100, 200]
        rq_suffix = self.client.set_test_params(fname, t_range_max=t_range_max, max_exec_time=max_exec_time)
        asyncio.run(
            self.client.emit_visualize_range(fname,
                                    request_id=f'zoom_{rq_suffix}',
                                    mz_range=mz_range,
                                    t_range=t_range)
        )
        self.assert_requests_ok()


    @unittest.skip("NotImplemented: fix test_visualize_zoomed_range")
    def test_visualize_two_ranges_sequentially(self):
        fname = 'TofDaq_Data_2021.07.30_small'

        rq_suffix = self.client.set_test_params(fname)
        asyncio.run(self.client.emit_visualize_range(fname, request_id=f"fullrange_{rq_suffix}"))
        self.assert_requests_ok()     # wait for rq to complete and verify exceptions

        max_exec_time = 30
        t_range_max = 10
        t_range=[5, t_range_max]
        mz_range=[100, 200]
        rq_suffix = self.client.set_test_params(fname, t_range_max=t_range_max, max_exec_time=max_exec_time)
        asyncio.run(
            self.client.emit_visualize_range(fname,
                                    request_id=f'zoom_{rq_suffix}',
                                    mz_range=mz_range,
                                    t_range=t_range)
        )
        self.assert_requests_ok()


    @unittest.skip("NotImplemented: fix test_visualize_zoomed_range")
    def test_visualize_two_ranges_parallel(self):
        fname = 'TofDaq_Data_2021.07.30_small'

        max_exec_time = 30    # for parallel rqs max_exec_time increases (TBT: how?)
        rq_suffix = self.client.set_test_params(fname, max_exec_time=max_exec_time)
        asyncio.run(self.client.emit_visualize_range(fname, request_id=f"fullrange_{rq_suffix}"))

        max_exec_time = 30
        t_range_max = 10
        t_range=[5, t_range_max]
        mz_range=[100, 200]
        rq_suffix = self.client.set_test_params(fname, t_range_max=t_range_max, max_exec_time=max_exec_time)
        asyncio.run(
            self.client.emit_visualize_range(fname,
                                    request_id=f'zoom_{rq_suffix}',
                                    mz_range=mz_range,
                                    t_range=t_range)
        )
        self.assert_requests_ok()


    @unittest.skip("TODO: fix data for input files, maybe extend max_exec_time")
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