#!/bin/pyton3

import unittest
import asyncio
import threading

import time
import asynctest

from TestClient import BaseTestClient, BaseTestClientNamespace, start_client_as_daemon


class TestBaseTestClient(asynctest.TestCase):
    def setUp(self) -> None:
        self.client = start_client_as_daemon()
        return super().setUp()

    def tearDown(self) -> None:
        asyncio.run(self.client.join_requests())
        self.client.stop_client('unittest tearDown')
        return super().tearDown()

    def test_visualize_full_range(self):
        fname = 'TofDaq_Data_2021.07.23_02h13m40s'
        rq_suffix = self.client.set_test_params(fname)
        asyncio.run(self.client.emit_visualize_range(fname, request_id=f"fullrange_{rq_suffix}"))


if __name__ == '__main__':
   unittest.main()