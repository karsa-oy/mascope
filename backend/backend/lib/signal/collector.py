# -*- coding: utf-8 -*-
"""Define classes to collect data from KEncoder processes and store it in
a sparse matrix.

Created on Tue Apr 09 17:53:44 2019
"""

import numpy as np
import h5sparse
from collections import defaultdict
from threading import Thread

# from .segment import KSegmentSequence


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
