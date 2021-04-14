# -*- coding: utf-8 -*-
"""Define classes to collect data from KEncoder processes and store it in
a sparse matrix.

Created on Tue Apr 09 17:53:44 2019
"""

import numpy as np
import dask.array as da

import os
import asyncio
import h5sparse
import array
import xarray
import sparse
import time

from collections import defaultdict
from threading import Thread
from scipy.sparse import coo_matrix

# from .ksegment import KSegmentSequence


class ExtendableDataset():
    def __init__(self):
        pass


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
                 chunk_size=10
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

        self.data_array = xarray.DataArray()
        
        self.delayed_write = None
        self.group = '%04d' % 0


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
                group_no = (self.data_array.shape[dim_index] / self.chunk_size) - 1
                self.group = '%04d' % group_no
                self.delayed_write.to_dataset().to_zarr(self.path,
                                                        group=self.group,
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
            self.group = '%04d' % (int(self.group)+1)
            # Write (last, incomplete) delayed chunk
            self.delayed_write.to_dataset().to_zarr(self.path,
                                                    group=self.group,
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





class CollectorProcessor():
    def __init__(self):
        self._fitted = False
        self.borders = []
        self.segment_sequences = {}

    def fit(self, segment_borders):
        self.borders = segment_borders
        self.segment_sequences = {hash( (s0, s1) ): KSegmentSequence((s0, s1))
                                  for u, (s0, s1) in self.borders.items()
                                  }
        self._fitted = True

    def transform(self, results):
        if not self._fitted:
            raise Exception("Cannot transform before fitting")
        
        i, i0, i1, spec, approx, code, peaks = results
        segment_hash = hash((i0, i1))

        self.segment_sequences.get(segment_hash).append(i, spec, approx, code, peaks)

        results = {'ridge_lines': self.segment_sequences.filter_ridges(min_len=3),

                   }
        return results

class KCollector(Thread):
    """ Thread to get signal processing results per segment.

    """

    def __init__(self,
                 queue_in,
                 processor=CollectorProcessor()
                 ):

        Thread.__init__(self)

        self.queue_in = queue_in
        self.processor = processor
        self.results = defaultdict(dict)

    def run(self):
        """Main loop
        
        """
        
        # Main loop
        while True:
            data = self.queue_in.get()
            # Received results
            if data:
                # self.processor.transform(data)
                speci = data.get('specis')[0] #XXX first speci as the key
                u = data.get('u')
                snos = data.get('snos')
                spec = data.get('spec')
                approx = data.get('approx')
                code = data.get('code')
                peaks = data.get('peaks')

                segment = {'spec': spec,
                           'approx': approx,
                           'code': code
                           }

                self.results[speci].update( {u: segment} )

            # Received poison pill
            else:
                # Got None
                if data is None:
                    # TODO: Currently None should never be received
                    pass
                else:
                    # TODO: Currently False is never received
                    break


class KCollector_old(Thread):
    """ Thread to get signal processing results per segment and combine
    them together.
    
    KCollector should be instantiated separately per acquisition
    
    Attributes
    ----------
    queue_in : Queue
        Queue to collect data from
    barrier : Barrier
        Barrier instance shared among KSignalProcessor threads for sync
    active_events : list
        list of Events per KEncoder, indicating whether they are still 
        processing
    cm_shape : tuple
        shape of the data matrix
    queue_out : Queue
        Queue to forward the results into
    collecting : bool
        flag telling if collecting
    collected : int
        Number of code segments collected
    code_matrix : IncrementalCoo
        IncrementalCoo sparse matrix to store the code

    """
    
    def __init__(self,
                 queue_in,
                 barrier,
                 active_events,
                 cm_shape,
                 queue_out=None):
        """Initialize self

        Parameters
        ----------
        queue_in : Queue
            Queue to collect data from
        barrier : Barrier
            Barrier instance shared among KSignalProcessor threads for sync
        active_events : list
            list of Events per KEncoder, indicating whether they are still 
            processing
        cm_shape : tuple
            shape of the data matrix
        queue_out : Queue, optional
            Queue to forward the results into if desired. Default is None.
        """
        
        Thread.__init__(self)
        self.queue_in = queue_in # Queues to get the results (code)
        self.barrier = barrier # Barrier to synchronize KScenthound threads
        self.active_events = active_events # Events flagging the status of workers
        self.cm_shape = cm_shape # Shape of the code matrix
        self.queue_out = queue_out # Queue to forward results (code) to
        self.collecting = False # Flag telling whether collection is active
        self.collected = 0 # Number of code segments collected
        # Instantiate IncrementalCOO sparse matrix for the code
        self.code_matrix = IncrementalCOO(self.cm_shape, np.float64)

    def run(self):
        """Main loop
        
        Loop while any of the workers is active, get from the 'queue_in'
        and store into 'code_matrix'
        """
        
        # Main loop. Loop until break (None) got from all queues
        while True:
            self.collecting = True # Set flag
            # Check if any processes are active
            is_active = [ e.is_set() for e in self.active_events ]
            processing = np.array(is_active).any() # Boolean, any process active
            if not processing and self.queue_in.qsize()==0:
                # No active processes and queue_in empty
                break
            # Try to get data from queue
            try:
                res = self.queue_in.get(timeout=.5)
            except:
                continue # Queue empty
            i, s0, s1, code = res # Unpack
            ind = code > 0 # Indices of non-zero values
            snos = np.arange(s0, s1) # Sample numbers
            ii = np.repeat(i, len(snos)) # Index of the spectrum
            self.code_matrix.extend(snos[ind], ii[ind], code[ind]) # Store results
            # Forward processing results
            if self.queue_out is not None:
                self.queue_out.put((i, s0, s1, code))
            self.collected += 1 # Increment counter
        # Collection finished
        if self.queue_out is not None:
            self.queue_out.put(None)
        self.collecting = False # Reset flag
        # Wait for all threads to finish
        self.barrier.wait()
        # Exit

    def compile_results(self, s0, s1, i0, i1, D=None):
        """Helper function to read code and calculate signal reconstruction

        Parameters
        ----------
        s0 : int
            Index of first sample
        s1 : int
            Index of last sample
        i0 : int
            Index of first spectrum
        i1 : int
            Index of last spectrum
        D : csr, optional
            Peak dictionary sparse matrix, used to reconstruct the signal.
            The default is None.

        Returns
        -------
        sub_code : array
            Mean code inside given indices
        approx : array or None
            Signal approximation (dot(D, code)) if D was given.
        """
        
        code = self.code_matrix.tocsc()
        sub_code = code[s0:s1, i0:i1].toarray()
        approx = None
        if D is not None:
            # Calculate signal reconstruction (approximation)
            sub_D = D[s0:s1, s0:s1].toarray()
            approx = np.dot(sub_D.T, sub_code)
            approx = np.mean(approx, axis=1)
        sub_code = np.mean(sub_code, axis=1)
        return sub_code, approx

    def write_to_file(self, filename):
        """Write the code matrix to h5 file

        Writes the 'code_matrix' into given h5 file, into dataset
        '/Karsa/code'. Overwrites in case the dataset exists.

        Parameters
        ----------
        filename : str
            Filename to write into
        """
        print('Writing code matrix to %s' %filename)
        code = self.code_matrix.tocsc()
        grp = u'//Karsa//code'
        with h5sparse.File(filename, 'r+') as h5f:
            if grp in h5f:
                # Delete previous results if exist
                del(h5f[grp])
            # Write code matrix to file
            h5f.create_dataset(grp, data=code)


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
