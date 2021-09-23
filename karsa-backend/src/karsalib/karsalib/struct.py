import dask.array as da
import numpy as np
import array
import xarray
import sparse
import time
import inspect
from multiprocessing import Event, Lock, cpu_count
from queue import Empty, Full
from scipy.sparse import coo_matrix
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


class AttrDict(dict):
    """Dict object that allows accessing values like attributes
    (dot notation).
    Example:
    d = AttrDict({'a': 0})  # initialize AttrDict with a dict
    d.a                     # returns 0
    """
    def __init__(self, *args, **kwargs):
        """Initialize self
        """
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

class LRUDict(dict):
    def __init__(self, capacity: int, *args, **kwargs):
        self.capacity = capacity
        self.lru_keys = []
        self.lock = Lock()
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        with self.lock:
            data = super().__getitem__(key)
            self.lru_keys.remove(key)
            self.lru_keys.append(key)
            return data

    def __setitem__(self, key, value):
        with self.lock:
            super().__setitem__(key, value)
            if key in self.lru_keys:
                self.lru_keys.remove(key)
            self.lru_keys.append(key)
            if len(self.lru_keys) > self.capacity:
                k = self.lru_keys.pop(0)
                super().__delitem__(k)

class ExtendableDataArray():
    """Class to collect data incrementally into a xarray.DataArray
    
    ...

    Attributes
    ----------
    path : str, optional
        Path into which write the contents of the array (zarr),
        by default None. If None, no writing.
    array_module : module
        Python array module to use as the xarray back-end
    dtype : dtype
        dtype of data_array
    data_array : DataArray
        DataArray into which the data is collected

    """
    
    def __init__(self,
                 path=None,
                 array_module=da,
                 dtype=np.float32,
                 sparse=False,
                 chunk_size=10,
                 persist=False,
                 ):
        """Initialize self

        Parameters
        ----------
        path : str, optional
            Path into which write the contents of the array (zarr),
            by default None. If None, no writing.
        array_module : module, optional
            Python module to use as xarray backend, by default dask.array.
        dtype : dtype, optional
            Array data type, by default numpy.float32
        sparse : bool, optional
            Whether to store the data in sparse.COO format, by default False.
        """

        self.path = path
        self.array_module = array_module
        self.dtype = dtype
        self.sparse = sparse
        self.chunk_size = chunk_size
        self.persist = persist

        self.data_array = xarray.DataArray()
        
        self.delayed_write = None
        self.group = -1

    def __getattr__(self, name):
        """Override standard getattr behaviour.

        Standard behaviour when getting ExtendableDataArray attributes.
        If requested attribute not in ExtendableDataArray, try to get it
        from the encapsulated DataArray object, self.data_array.
        If not there either, raise AtteibuteError.
        """

        try:
            return getattr(self.data_array, name)
        except AttributeError:
            raise AttributeError("'ExtendableDataArray' object has no attribute '%s'"
                                 %name
                                 )
    
    def __getitem__(self, indices):
        """Make encapsulated DataArray object subscriptable
        """
        return self.data_array.__getitem__(indices)

    def init_array(self, dims, data=None, coords=None, name=''):
        """Initalize the data array.

        Parameters
        ----------
        dims : tuple
            Tuple of dimension labels
        data : array, optional
            Initial data, by default None. If None,
            empty array is initialized.
        coords : list, optional
            List of coordinate vectors, one per dimension. Required
            if 'data' argument is not None, by default None.
        name : str, optional
            Name of the data array, by default ''.
        """

        if coords is None:
            # Create empty coords
            coords = [[]]*len(dims)
        
        # Initialize the DataArray
        self.data_array = xarray.DataArray(data,
                                           dims=dims,
                                           coords=coords,
                                           name=name
                                           )
        # Initialize file
        if self.path is not None:
            self.data_array.to_dataset().to_zarr(
                                            self.path,
                                            mode='w-' # Create
                                            )

    def combine_first(self, data, coords):
        data = self.array_module.array(data, dtype=self.dtype)

        extension = xarray.DataArray(data,
                                     dims=self.data_array.dims,
                                     coords=coords,
                                     name=self.data_array.name
                                     )

        self.data_array = self.data_array.combine_first(extension)

    def extend_array(self,
                     data,
                     coords,
                     dim,
                     callback=None,
                     cargs=(),
                     ckwargs={}
                     ):
        """Extend data array with new data.
        
        Parameters
        ----------
        data : array
            Array of data to be added into the existing array.
        coords : list
            Coordinate vectors for the data to be added.
        dim : 
            Dimension along which to concatenate.
        callback : callable, optional
            Callback function to execute at the end of this method,
            by default None.
        cargs : tuple, optional
            Arguments to the callback function, by default empty tuple.
        """

        # t0 = time.time()

        # Dimension check            
        dims = self.data_array.dims
        try:
            dim_index = dims.index(dim)
        except ValueError:
            raise ValueError("Failed to extend array. Input argument 'dim' " +
                             "must be one of the dimensions of the existing array")
        
        if self.sparse:
            data = sparse.COO(data)

        data = self.array_module.array(data, dtype=self.dtype)

        extension = xarray.DataArray(data,
                                     dims=dims,
                                     coords=coords,
                                     name=self.data_array.name
                                     )

        if self.data_array.shape[dim_index] > 0:
            # Extend non-empty array
            to_concat = [ self.data_array, extension ]
        else:
            # Extend empty array
            to_concat = [ extension ]

        # Concatenate
        self.data_array = xarray.concat(to_concat,
                                        dim=dim
                                        )
        if self.persist:
            self.data_array = self.data_array.persist()
        # t1 = time.time()
        # print("Concatenation took: %.2f seconds" %(t1-t0))
        # t0 = time.time()

        # Incremental write to file
        if self.path is not None:
            if self.delayed_write is None:
                # Start new delayed chunk, to be written later
                self.delayed_write = extension
            else:
                # Collect delayed chunk to be written later
                self.delayed_write = xarray.concat([self.delayed_write, extension],
                                                   dim=dim
                                                   )
            if self.delayed_write.shape[dim_index] == self.chunk_size:
                # Write delayed chunk
                self.group = (self.data_array.shape[dim_index] / self.chunk_size) - 1
                group_name = '%04d' % self.group
                self.delayed_write.to_dataset().to_zarr(self.path,
                                                        group=group_name,
                                                        mode='a',
                                                        compute=True
                                                        )
                self.delayed_write = None

        # t1 = time.time()
        # print("Write operation took: %.2f seconds" %(t1-t0))

        # Optional callback function
        if callback is not None:
            return callback(*cargs, **ckwargs)

        return extension

    def flush(self):
        if self.delayed_write is not None:
            group_name = '%04d' % (self.group+1)
            # Write (last, incomplete) delayed chunk
            self.delayed_write.to_dataset().to_zarr(self.path,
                                                    group=group_name,
                                                    mode='a',
                                                    compute=True
                                                    )
            self.delayed_write = None

    def assign_column(self, data, col):
        """Assign data into an existing data array column

        Parameters
        ----------
        data : array
            Array to assign
        col : int
            Column index into which to assign the data

        Raises
        ------
        NotImplementedError
            Raised if trying to assign dask array
        """

        if self.array_module == np:
            self.data_array[col] = data
        else:
            # TODO: Implement for dask array (using da.concatenate)
            raise NotImplementedError("Column assignment not implemented " + 
                                      "for array module %s" %str(self.array_module)
                                      )

class IncrementalCOO():
    """Sparse matrix structure optimized for incremental construction.
    
    Class to construct COO-type sparse matrix incrementally.
    
    Attributes
    ----------
    dtype : int32, int64, float32, float64
        dtype of the array
    shape : tuple
        shape of the array
    rows : array
        array holding row indices
    cols : array
        array holding column indices
    data : array
        array holding values

    """
    
    def __init__(self, dtype):
        """Initialize self
        
        Parameters
        ----------
        shape : tuple
            Shape of the matrix to initialize
        dtype : int32, int64, float32, float64
            Data type of the array to initialize

        Raises
        ------
        Exception
            If given dtype is not supported.
        """
        
        if dtype is np.int32:
            type_flag = 'i'
        elif dtype is np.int64:
            type_flag = 'l'
        elif dtype is np.float32:
            type_flag = 'f'
        elif dtype is np.float64:
            type_flag = 'd'
        else:
            raise Exception('Dtype not supported.')

        self.dtype = dtype
        self.rows = array.array('i')
        self.cols = array.array('i')
        self.data = array.array(type_flag)

    def extend(self, rows, cols, data):
        """Add data to matrix

        Parameters
        ----------
        rows : array
            Row indices
        cols : array
            Column indices
        data : array
            Data
        """

        self.rows.extend(rows)
        self.cols.extend(cols)
        self.data.extend(data)

    def tocoo(self):
        """Return matrix as COO sparse matrix

        Returns
        -------
        coo_matrix
            Return as scipy.sparse.coo_matrix

        """

        rows = np.frombuffer(self.rows, dtype=np.int32)
        cols = np.frombuffer(self.cols, dtype=np.int32)
        data = np.frombuffer(self.data, dtype=self.dtype)

        shape = ( max(rows)+1, max(cols)+1 )

        return coo_matrix( (data, (rows, cols)),
                           shape=shape
                           )

    def tocsc(self):
        """Return matrix as CSC sparse matrix
        
        Convert first to COO and then CSC.

        Returns
        -------
        csc_matrix
            Return as scipy.sparse.csc_matrix

        """
        
        return self.tocoo().tocsc()

class QConnect(Thread):
    OUT_Q_LIMIT = cpu_count()
    CACHE_LIMIT = 1000000   # TODO: number?

    def __init__(self, in_q=None, out_q=None, shutdown_event=None):
        Thread.__init__(self)
        self.in_q = in_q
        self.out_q = out_q
        self.shutdown_event = shutdown_event
        self.input_ready = Event()
        self.input_ready.set()
        self.cache = []

    def put(self, data):
        self.input_ready.wait()
        self.input_ready.clear()
        self.in_q.put(data)
        self.input_ready.wait()

    def get(self, *args, **kwargs):
        return self.out_q.get(*args, **kwargs)

    def cache_put(self, data):
        if len(self.cache) > self.CACHE_LIMIT:
            raise Full
        self.cache.insert(0, data)

    def cache_get(self):
        data = self.cache.pop()
        return data

    def fits_filter(self, data):
        return False

    def run(self):
        while not self.shutdown_event.is_set():
            data = None
            try:
                data = self.in_q.get_nowait()
                # print('in_q.get', data.get('request_id', ':'.join([data.get('name','?'), data.get('key','?')])))
            except Empty:
                pass
            except KeyboardInterrupt:
                self.input_ready.set()
                break
            if data:
                if self.fits_filter(data):
                    continue
                try:
                    self.cache_put(data)
                except Full as e:
                    print("Cache overflow -- skipping input!")
                finally:
                    self.input_ready.set()
            if self.out_q.qsize() >= self.OUT_Q_LIMIT:
                time.sleep(.01)
                continue
            data = self.cache_get()
            if data:
                self.out_q.put(data)
                # print('out_q.put', data.get('request_id', ':'.join([data.get('name','?'), data.get('key','?')])))
            else:
                time.sleep(.01)
        self.cache = None
        print(f"Exit from {self.__class__.__name__} thread")

class CacheQ(QConnect):
    """Cached queue emulator: works like a queue with ability to manipulate its content."""
    def __init__(self, cache_key, *arg, **kwarg):
        super().__init__(*arg, **kwarg)
        self.cache = dict()
        self.cache_key_separator = kwarg.get('cache_key_separator', '/')
        self.cache_key = cache_key.split(self.cache_key_separator)
        self.cache_index = len(self.cache_key) * [0]
        self.cache_index[0] = -1
        self.lock = Lock()
        self.in_q_filters = []

    def cache_put(self, data):
        keys = []
        for k in self.cache_key:
            keys.append(data.get(k, 'default'))
        cache_depth = len(keys) - 1
        cache_level = self.cache
        with self.lock:
            for i, k in enumerate(keys):
                if k not in cache_level:
                    cache_level[k] = [] if i == cache_depth else {}
                cache_level = cache_level[k]
            cache_level.insert(0, data)

    def _inc_cache_level_index(self, dic, index):
        step = min(len(dic), index + 1)
        next_index = step % len(dic)
        index_shift = step // len(dic)
        return next_index, index_shift

    def _inc_cache_index(self):
        cache_level = self.cache
        for i in range(len(self.cache_index)):
            self.cache_index[i], shift = self._inc_cache_level_index(cache_level, self.cache_index[i])
            if not shift:
                break
            next_key = list(cache_level.keys())[self.cache_index[i]]
            cache_level = cache_level[next_key]

    def cache_get(self):
        self.lock.acquire()
        cache_level_keys = []
        cache_level_dics = []
        cache_level = self.cache
        cache_level_dics.append(cache_level)
        try:
            self._inc_cache_index()
        except:
            self.lock.release()
            return None
        for i in self.cache_index:
            try:
                key = list(cache_level.keys())[i]
            except IndexError:
                self.lock.release()
                return self.cache_get()
            cache_level = cache_level[key]
            cache_level_dics.append(cache_level)
            cache_level_keys.append(key)
        data = cache_level.pop()
        if not cache_level:             # no more data in this cache element - clean up
            for d, k in reversed(list(zip(cache_level_dics, cache_level_keys))):
                if not d[k]:
                    del d[k]
        self.lock.release()
        return data

    def cache_delete_key(self, key):
        with self.lock:
            if self.in_q:
                # set ignore-marker for data, which is pending in in_q
                self.in_q_filters.append(key)
                self.in_q.put({'name': '__stop_fits_filter', 'key': key})
            # delete cache hierarchy for the key
            level_keys = key.split(self.cache_key_separator)
            cache_level = self.cache
            key_to_delete = level_keys.pop(0)
            while level_keys:
                cache_level = cache_level[key_to_delete]
                key_to_delete = level_keys.pop(0)
            if key_to_delete in cache_level:
                del cache_level[key_to_delete]

    def fits_filter(self, data):
        with self.lock:
            # filter out ignore-marker package
            if data.get('name') == '__stop_fits_filter':
                # print('__stop_fits_filter', data['key'])
                self.in_q_filters.remove(data['key'])
                return True
            # check if input data fits any filter element
            for filter in self.in_q_filters:
                fit = True
                for k, v in zip(self.cache_key, filter.split(self.cache_key_separator)):
                    if data.get(k) != v:
                        fit = False
                        break
                if fit:
                    # print('fits_filter', filter)
                    return True
            return False

    def cache_size(self, cache_level=None):
        cache_level = cache_level or self.cache
        if isinstance(cache_level, list):
            return len(cache_level)
        return sum([self.cache_size(v) for v in cache_level.values()])

class SubscriptableQueue(object):
    """Subscriptable Queue object
    
    Threads or Processes can subscribe to this object with
    a unique identifier, allowing synchronization between
    producer and consumer threads. It is intended to be used
    within the producer thread in place of a standard Queue, in
    cases where multiple consumers need to have simultaneous access 
    to the queue. Use instances of 'QueueSubscription' in place 
    of a standard Queue within the consumer threads to allow direct
    replacement of a Queue object.

    Attributes
    ----------
    queues : dict
        Dictionary holding the subscriptions to this instance,
        keys are unique identifiers for each subscriber and the
        values are their corresponding (standard) Queue objects.
    """

    def __init__(self):
        """Initialize self
        """

        self.queues = {}

    def __bool__(self):
        """
        Returns
        -------
        bool
            Returns True if there are any subscribers, False otherwise
        """
        return len(self.queues) > 0

    def put(self, val):
        """Put value to the queue of each subscriber

        Only the producer thread should call the put method, to avoid
        incompatibilities (i.e. to keep consumers independent of each other).

        Parameters
        ----------
        val : any
            Data to put
        """

        for ident, q in self.queues.items():
            q.put(val)

    def get(self, ident, *args, **kwargs):
        """Get from the queue with key 'ident'. Extra arguments will
        be passed to the queue.get() method.

        Parameters
        ----------
        ident : str
            Key of the subscriber

        Returns
        -------
        any
            Return the next object in the queue
        """

        return self.queues.get(ident).get(*args, **kwargs)

    def get_nowait(self, ident, *args, **kwargs):
        """Get without blocking from the queue with key 'ident'.
        Extra arguments will be passed to the queue.get_nowait() method.

        Parameters
        ----------
        ident : str
            Key of the subscriber

        Returns
        -------
        any
            Return the next object in the queue (if any)
        """
        
        return self.queues.get(ident).get_nowait(*args, **kwargs)

    def qsize(self, ident, *args, **kwargs):
        """Get size of the queue with key 'ident'

        Parameters
        ----------
        ident : str
            Key of the subscriber

        Returns
        -------
        int
            Queue size
        """

        return self.queues.get(ident).qsize(*args, **kwargs)

    def subscribe(self, ident):
        """Subscribe to this instance

        Parameters
        ----------
        ident : str
            Key to subscribe with, must be unique

        Raises
        ------
        Exception
            Exception is raised if a subscriber with the same key exists
            already.
        """

        if ident in self.queues.keys():
            raise Exception('name %s already subscribed' %ident)
        else:
            self.queues.update({ident: Queue()})

    def close(self):
        """Close all queues
        """

        for ident, q in self.queues.items():
            q.close()
            
    def join_thread(self):
        """Join all queue threads
        """

        for ident, q in self.queues.items():
            q.close()
            
class QueueSubscription():
    """Object to use in place of a standard Queue within a consumer thread,
    when using SubscriptableQueue within the producer thread.

    Attributes
    ----------
    q : SubscriptableQueue
        Instance to subscribe to
    ident : str
        Unique identifier of this subscription
    """

    def __init__(self, subscriptable_q, ident=None):
        """Initialize self

        Subscribe to the 'subscriptable_q' with the key 'ident'.
        If 'ident' is not given, it will be automatically generated.

        Parameters
        ----------
        subscriptable_q : SubscriptableQueue
            Instance to subscribe to
        ident : str, optional
            Unique identifier of this subscription, by default None.
            If None, it will be automatically generated.
        """

        self.q = subscriptable_q
        # Subscribe to a subscriptable queue
        if ident is None:
            ident = generate_unique_key()
        self.ident = ident
        self.q.subscribe(ident)

    def get(self, *args, **kwargs):
        """Get from the queue

        Returns
        -------
        any
            Next object in the queue
        """

        # Get from the queue
        return self.q.get(self.ident, *args, **kwargs)

    def get_nowait(self, *args, **kwargs):
        """Get from the queue without waiting

        Returns
        -------
        any
            Next object in the queue (if not empty)

        Raises
        ------
        Exception
            Raises an exception if the queue is empty
        """

        try:
            return self.q.get_nowait(self.ident, *args, **kwargs)
        except Empty:
            raise Empty

    def qsize(self, *args, **kwargs):
        """Get queue size

        Returns
        -------
        int
            Number of objects in the queue
        """

        return self.q.qsize(self.ident, *args, **kwargs)


class FSWatcher:
    class FSEventHandler(PatternMatchingEventHandler):
        def __init__(self, client, mask):
            self.client = client
            super().__init__(patterns=[mask,])

        def on_created(self, event):
            self.client.on_filesystem_object_created(event.src_path)

        def on_deleted(self, event):
            self.client.on_filesystem_object_deleted(event.src_path)

    def log(self, *arg, **kwarg):
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg, **kwarg)

    def __init__(self, client, target_attrs, recursive=False):
        self.client = client
        self.target_attrs = target_attrs
        self.recursive = recursive
        self.observer = Observer()
        self.handler = self.FSEventHandler(self.client, self.target_attrs['mask'])

    def start(self):
        self.observer.schedule(self.handler, self.target_attrs['path'], recursive=self.recursive)
        self.observer.start()
        self.log('started')

    def stop(self):
        self.observer.stop()
        self.observer.join()
        self.log('stopped')

    def run(self):
        self.start()
        try:
            while not self.client.shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.log('KeyboardInterrupt')
            self.client.shutdown_event.set()
        except Exception as e:
            self.log(str(e))
            self.client.shutdown_event.set()
        self.stop()

    def run_as_daemon(self):
        Thread(target=self.run).start()
