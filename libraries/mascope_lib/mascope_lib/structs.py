import inspect
import os
import time
from threading import Thread

import dask.array as da
import numpy as np
import sparse
import xarray
import zarr
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

import mascope_runtime as runtime

logger = runtime.logger.service('standard-lib')

class AttrDict(dict):
    """Dict object that allows accessing values like attributes
    (dot notation).
    Example:
    d = AttrDict({'a': 0})  # initialize AttrDict with a dict
    d.a                     # returns 0
    """

    def __init__(self, *args, **kwargs):
        """Initialize self"""
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class ExtendableDataArray:
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

    @staticmethod
    def get_zarr_synchronizer(zarr_path):
        parent_dir = os.path.dirname(zarr_path)
        sync_name = zarr_path.split(os.path.sep)[-1].replace(".zarr", ".sync")
        sync_path = os.path.sep.join([parent_dir, sync_name])
        return zarr.ProcessSynchronizer(sync_path)

    def __init__(
        self,
        path=None,
        array_module=da,
        dtype=np.float32,
        sparse=False,
        chunk_size=10,
        persist=False,
        overwrite=False,
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
        if path is not None:
            self.sync = self.get_zarr_synchronizer(self.path)
        self.array_module = array_module
        self.dtype = dtype
        self.sparse = sparse
        self.chunk_size = chunk_size
        self.persist = persist
        self.overwrite = overwrite

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
            raise AttributeError(
                "'ExtendableDataArray' object has no attribute '%s'" % name
            )

    def __getitem__(self, indices):
        """Make encapsulated DataArray object subscriptable"""
        return self.data_array.__getitem__(indices)

    def init_array(self, dims, data=None, coords=None, name=""):
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
            coords = [[]] * len(dims)

        # Initialize the DataArray
        self.data_array = xarray.DataArray(data, dims=dims, coords=coords, name=name)
        # Initialize file
        if self.path is not None:
            self.data_array.to_dataset().to_zarr(
                self.path, mode="w" if self.overwrite else "w-"
            )

    def combine_first(self, data, coords):
        data = self.array_module.array(data, dtype=self.dtype)

        extension = xarray.DataArray(
            data, dims=self.data_array.dims, coords=coords, name=self.data_array.name
        )

        self.data_array = self.data_array.combine_first(extension)

    def extend_array(self, data, coords, dim, callback=None, cargs=(), ckwargs={}):
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
            raise ValueError(
                "Failed to extend array. Input argument 'dim' "
                + "must be one of the dimensions of the existing array"
            )

        if self.sparse:
            data = sparse.COO(data)

        data = self.array_module.array(data, dtype=self.dtype)

        extension = xarray.DataArray(
            data, dims=dims, coords=coords, name=self.data_array.name
        )

        if self.data_array.shape[dim_index] > 0:
            # Extend non-empty array
            to_concat = [self.data_array, extension]
        else:
            # Extend empty array
            to_concat = [extension]

        # Concatenate
        self.data_array = xarray.concat(to_concat, dim=dim)
        if self.persist:
            self.data_array = self.data_array.persist()

        # Incremental write to file
        if self.path is not None:
            if self.delayed_write is None:
                # Start new delayed chunk, to be written later
                self.delayed_write = extension
            else:
                # Collect delayed chunk to be written later
                self.delayed_write = xarray.concat(
                    [self.delayed_write, extension], dim=dim
                )
            if self.delayed_write.shape[dim_index] == self.chunk_size:
                # Write delayed chunk
                self.group = (self.data_array.shape[dim_index] / self.chunk_size) - 1
                group_name = "%04d" % self.group
                self.delayed_write.to_dataset().to_zarr(
                    self.path,
                    group=group_name,
                    mode="a",
                    synchronizer=self.sync,
                    consolidated=False,
                    compute=True,
                )
                self.delayed_write = None

        # Optional callback function
        if callback is not None:
            return callback(*cargs, **ckwargs)

        return extension

    def flush(self):
        if self.delayed_write is not None:
            group_name = "%04d" % (self.group + 1)
            # Write (last, incomplete) delayed chunk
            self.delayed_write.to_dataset().to_zarr(
                self.path,
                group=group_name,
                mode="a",
                synchronizer=self.sync,
                consolidated=False,
                compute=True,
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
            raise NotImplementedError(
                "Column assignment not implemented "
                + "for array module %s" % str(self.array_module)
            )


class FSWatcher:
    class FSEventHandler(PatternMatchingEventHandler):
        def __init__(self, client, mask):
            self.client = client
            if not isinstance(mask, list):
                mask = [
                    mask,
                ]
            super().__init__(patterns=mask)

        def log(self, *arg):
            logger.info(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg)

        def on_created(self, event):
            try:
                self.client.on_filesystem_object_created(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass

        def on_modified(self, event):
            try:
                self.client.on_filesystem_object_modified(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass

        def on_deleted(self, event):
            try:
                self.client.on_filesystem_object_deleted(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass

        def on_moved(self, event):
            try:
                self.client.on_filesystem_object_created(event.dest_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass
            try:
                self.client.on_filesystem_object_deleted(event.src_path)
            except AttributeError:
                pass
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass

    def log(self, *arg):
        logger.info(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg)

    def __init__(self, client, target_attrs, recursive=False):
        self.client = client
        self.target_attrs = target_attrs
        self.recursive = recursive
        self.observer = Observer()
        self.handler = self.FSEventHandler(self.client, self.target_attrs["mask"])

    def start(self):
        self.observer.schedule(
            self.handler, self.target_attrs["path"], recursive=self.recursive
        )
        self.observer.start()
        self.log("started watching", self.target_attrs)

    def stop(self):
        self.observer.stop()
        self.observer.join()
        self.log("stopped")

    def run(self):
        self.start()
        while not self.client.shutdown_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                self.log("KeyboardInterrupt")
                self.client.shutdown_event.set()
            except Exception as e:
                self.log(f"Exception {e.__class__.__name__}({str(e)})")
                pass
        self.stop()

    def run_as_daemon(self):
        Thread(target=self.run).start()
