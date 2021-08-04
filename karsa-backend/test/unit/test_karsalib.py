import unittest
from multiprocessing import Event, Queue
from queue import Empty
import time

from karsalib.struct import CacheQ, LRUDict


cache_q_single_level = {
   "id_0": [
      {
         "request_id": "id_0", 
         "data_type": "type_0",
         "value": 18
      },
      {
         "request_id": "id_0", 
         "data_type": "type_3",
         "value": 15
      },
      {
         "request_id": "id_0", 
         "data_type": "type_0",
         "value": 12
      },
      {
         "request_id": "id_0",
         "data_type": "type_3",
         "value": 9
      },
      {
         "request_id": "id_0",
         "data_type": "type_0",
         "value": 6
      },
      {
         "request_id": "id_0",
         "data_type": "type_3",
         "value": 3
      },
      {
         "request_id": "id_0",
         "data_type": "type_0",
         "value": 0
      }
   ],
   "id_1": [
      {
         "request_id": "id_1",
         "data_type": "type_1",
         "value": 19
      },
      {
         "request_id": "id_1",
         "data_type": "type_4",
         "value": 16
      },
      {
         "request_id": "id_1",
         "data_type": "type_1",
         "value": 13
      },
      {
         "request_id": "id_1",
         "data_type": "type_4",
         "value": 10
      },
      {
         "request_id": "id_1",
         "data_type": "type_1",
         "value": 7
      },
      {
         "request_id": "id_1",
         "data_type": "type_4",
         "value": 4
      },
      {
         "request_id": "id_1",
         "data_type": "type_1",
         "value": 1
      }
   ],
   "id_2": [
      {
         "request_id": "id_2",
         "data_type": "type_5",
         "value": 17
      },
      {
         "request_id": "id_2",
         "data_type": "type_2",
         "value": 14
      },
      {
         "request_id": "id_2",
         "data_type": "type_5",
         "value": 11
      },
      {
         "request_id": "id_2",
         "data_type": "type_2",
         "value": 8
      },
      {
         "request_id": "id_2",
         "data_type": "type_5",
         "value": 5
      },
      {
         "request_id": "id_2",
         "data_type": "type_2",
         "value": 2
      }
   ]
}

cache_q_tripple_level = {
   "id_0": {
      "type_0": {
         "some_index_0": [
            {
               "request_id": "id_0",        
               "data_type": "type_0",       
               "some_index": "some_index_0",
               "value": 0
            }
         ],
         "some_index_6": [
            {
               "request_id": "id_0",        
               "data_type": "type_0",       
               "some_index": "some_index_6",
               "value": 6
            }
         ],
         "some_index_4": [
            {
               "request_id": "id_0",
               "data_type": "type_0",
               "some_index": "some_index_4",
               "value": 12
            }
         ],
         "some_index_2": [
            {
               "request_id": "id_0",
               "data_type": "type_0",
               "some_index": "some_index_2",
               "value": 18
            }
         ]
      },
      "type_3": {
         "some_index_3": [
            {
               "request_id": "id_0",
               "data_type": "type_3",
               "some_index": "some_index_3",
               "value": 3
            }
         ],
         "some_index_1": [
            {
               "request_id": "id_0",
               "data_type": "type_3",
               "some_index": "some_index_1",
               "value": 9
            }
         ],
         "some_index_7": [
            {
               "request_id": "id_0",
               "data_type": "type_3",
               "some_index": "some_index_7",
               "value": 15
            }
         ]
      }
   },
   "id_1": {
      "type_1": {
         "some_index_1": [
            {
               "request_id": "id_1",
               "data_type": "type_1",
               "some_index": "some_index_1",
               "value": 1
            }
         ],
         "some_index_7": [
            {
               "request_id": "id_1",
               "data_type": "type_1",
               "some_index": "some_index_7",
               "value": 7
            }
         ],
         "some_index_5": [
            {
               "request_id": "id_1",
               "data_type": "type_1",
               "some_index": "some_index_5",
               "value": 13
            }
         ],
         "some_index_3": [
            {
               "request_id": "id_1",
               "data_type": "type_1",
               "some_index": "some_index_3",
               "value": 19
            }
         ]
      },
      "type_4": {
         "some_index_4": [
            {
               "request_id": "id_1",
               "data_type": "type_4",
               "some_index": "some_index_4",
               "value": 4
            }
         ],
         "some_index_2": [
            {
               "request_id": "id_1",
               "data_type": "type_4",
               "some_index": "some_index_2",
               "value": 10
            }
         ],
         "some_index_0": [
            {
               "request_id": "id_1",
               "data_type": "type_4",
               "some_index": "some_index_0",
               "value": 16
            }
         ]
      }
   },
   "id_2": {
      "type_2": {
         "some_index_2": [
            {
               "request_id": "id_2",
               "data_type": "type_2",
               "some_index": "some_index_2",
               "value": 2
            }
         ],
         "some_index_0": [
            {
               "request_id": "id_2",
               "data_type": "type_2",
               "some_index": "some_index_0",
               "value": 8
            }
         ],
         "some_index_6": [
            {
               "request_id": "id_2",
               "data_type": "type_2",
               "some_index": "some_index_6",
               "value": 14
            }
         ]
      },
      "type_5": {
         "some_index_5": [
            {
               "request_id": "id_2",
               "data_type": "type_5",
               "some_index": "some_index_5",
               "value": 5
            }
         ],
         "some_index_3": [
            {
               "request_id": "id_2",
               "data_type": "type_5",
               "some_index": "some_index_3",
               "value": 11
            }
         ],
         "some_index_1": [
            {
               "request_id": "id_2",
               "data_type": "type_5",
               "some_index": "some_index_1",
               "value": 17
            }
         ]
      }
   }
}

cache_q_tripple_index_sequence = [
    [0, 0, 0], [1, 0, 0], [2, 0, 0],
    [0, 1, 0], [1, 1, 0], [2, 1, 0],
    [0, 0, 1], [1, 0, 1], [2, 0, 1],
    [0, 1, 1], [1, 1, 1], [2, 1, 1],
    [0, 0, 2], [1, 0, 2], [2, 0, 2],
    [0, 1, 2], [1, 1, 2], [2, 1, 2],
    [0, 0, 3], [1, 0, 3], [2, 0, 3],
    [0, 1, 3], [1, 1, 3], [2, 1, 3],
    [0, 0, 0]
]

class TestCacheQContents(unittest.TestCase):
   def setUp(self) -> None:
      return super().setUp()

   def tearDown(self) -> None:
      return super().tearDown()

   def test_single_level_cache(self):
      nentries = 20
      cache_q = CacheQ('request_id', None, None, None)
      for i in range(nentries):
         data = {'request_id': f'id_{i%3}', 'data_type': f'type_{i%6}', 'value': i}
         cache_q.cache_put(data)
      self.assertDictEqual(cache_q.cache, cache_q_single_level)

   def test_tripple_level_cache(self):
      nentries = 20
      cache_q = CacheQ('request_id/data_type/some_index', None, None, None)
      for i in range(nentries):
         data = {'request_id': f'id_{i%3}', 'data_type': f'type_{i%6}', 'some_index': f'some_index_{i%8}', 'value': i}
         cache_q.cache_put(data)
      self.assertDictEqual(cache_q.cache, cache_q_tripple_level)


class TestCacheQOperations(unittest.TestCase):
   """ With single process setup, no need for in_q and out_q and worker thread -
       just use cache_put/cache_get directly
   """
   def setUp(self) -> None:
      self.q1 = Queue()
      self.q2 = Queue()
      self.stop_event = Event()
      self.cache_q = CacheQ('request_id/data_type/some_index', self.q1, self.q2, self.stop_event)
      self.nentries = 20
      for i in range(self.nentries):
         data = {'request_id': f'id_{i%3}', 'data_type': f'type_{i%6}', 'some_index': f'some_index_{i%8}', 'value': i}
         self.cache_q.cache_put(data)
      return super().setUp()

   def tearDown(self) -> None:
      return super().tearDown()

   def test_ops(self):
      # verify sequence of cache_indices
      for i in range(25):
         self.cache_q._inc_cache_index()
         self.assertEqual(self.cache_q.cache_index, cache_q_tripple_index_sequence[i])
      # verify delete and size ops
      self.assertEqual(self.cache_q.cache_size(), 20)
      self.cache_q.cache_delete_key('id_1/type_4/some_index_2')
      self.assertEqual(self.cache_q.cache_size(), 19)

   def test_cache_get(self):
      n = 0
      while True:
         data = self.cache_q.cache_get()
         if data is None:
               break
         n += 1
      self.assertEqual(len(self.cache_q.cache), 0)
      self.assertEqual(n, self.nentries)


class TestThreadedCacheQ(unittest.TestCase):
   """ With multiprocess setup, worker thread is used"""
   def setUp(self) -> None:
      self.q1 = Queue()
      self.q2 = Queue()
      self.stop_event = Event()
      self.cache_q = CacheQ('request_id/data_type/some_index', self.q1, self.q2, self.stop_event)
      self.cache_q.start()    # start CacheQ worker thread
      self.nentries = 20
      return super().setUp()

   def tearDown(self) -> None:
      self.stop_event.set()
      return super().tearDown()

   def test_thread_proc_with_exposed_queues(self):
      time.sleep(1)   # pause main thread to test empty cycles of cache_q thread
      #
      for i in range(self.nentries):
         data = {'request_id': f'id_{i%3}', 'data_type': f'type_{i%6}', 'some_index': f'some_index_{i%8}', 'value': i}
         self.q1.put(data)    # if a cycle of in_q.puts is too quick, this may need some time to adapt to
         time.sleep(0.1)      # slower cache dict update in the worker thread
      # OUT_Q_LIMIT elements were pushed to cache_q.out_q
      self.assertEqual(self.cache_q.cache_size(), self.nentries - self.cache_q.OUT_Q_LIMIT)
      #
      n = 0
      while True:
         try:
               data = self.q2.get(timeout=.1)
               n += 1
         except Empty:
               break
      self.assertEqual(n, self.nentries)
      self.assertEqual(self.cache_q.cache_size(), 0)

   def test_thread_proc_with_hidden_queues(self):
      #
      for i in range(self.nentries):
         data = {'request_id': f'id_{i%3}', 'data_type': f'type_{i%6}', 'some_index': f'some_index_{i%8}', 'value': i}
         self.cache_q.put(data)  # 'put' wrapper uses heavier sync with worker thread - safety TBR
      # OUT_Q_LIMIT elements were pushed to cache_q.out_q
      self.assertEqual(self.cache_q.cache_size(), self.nentries - self.cache_q.OUT_Q_LIMIT)
      #
      n = 0
      while True:
         try:
               data = self.cache_q.get(timeout=.1)
               n += 1
         except Empty:
               break
      self.assertEqual(n, self.nentries)
      self.assertEqual(self.cache_q.cache_size(), 0)


class TestLRUDict(unittest.TestCase):
   def setUp(self) -> None:
      self.d = LRUDict(3)
      return super().setUp()

   def tearDown(self) -> None:
      return super().tearDown()

   def test_LRUDict_operations(self):
      with self.assertRaises(KeyError):
         v = self.d['a']
      with self.assertRaises(KeyError):
         del self.d['a']
      self.assertEqual(self.d.get('a', 'nothing'), 'nothing')
      self.assertEqual(list(self.d.keys()), [])
      self.assertEqual(list(self.d.values()), [])
      #
      self.d['a'] = 1
      self.d['b'] = 2
      self.d['c'] = 3
      self.assertEqual(sorted(list(self.d.keys())), ['a', 'b', 'c'])
      self.assertEqual(sorted(list(self.d.values())), [1, 2, 3])
      self.assertEqual(list(self.d.lru_keys), ['a', 'b', 'c'])
      self.d['d'] = 4
      self.assertEqual(sorted(list(self.d.keys())), ['b', 'c', 'd'])
      self.assertEqual(sorted(list(self.d.values())), [2, 3, 4])
      self.assertEqual(list(self.d.lru_keys), ['b', 'c', 'd'])
      a = self.d['c']
      a = self.d['b']
      self.assertEqual(sorted(list(self.d.keys())), ['b', 'c', 'd'])
      self.assertEqual(sorted(list(self.d.values())), [2, 3, 4])
      self.assertEqual(list(self.d.lru_keys), ['d', 'c', 'b'])
      self.d['e'] = 5
      self.assertEqual(sorted(list(self.d.keys())), ['b', 'c', 'e'])
      self.assertEqual(sorted(list(self.d.values())), [2, 3, 5])
      self.assertEqual(list(self.d.lru_keys), ['c', 'b', 'e'])




if __name__ == '__main__':
   unittest.main()