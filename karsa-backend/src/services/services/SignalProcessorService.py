import asyncio
import numpy as np

from threading import Thread
from multiprocessing import (Barrier,
                             Event,
                             Queue,
                             RawArray,
                             Value,
                             cpu_count)
from queue import Empty

from scipy.signal import find_peaks

from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.struct import AttrDict, ExtendableDataArray
from karsalib.util import parse_cmd_args
from scenthound.kfeeder import KFeeder, FeederProcessor
from scenthound.kworker import KEncoder
from scenthound.kcollector import KCollector
# from scenthond.kpeak import load_peak_dict

from services.FileIoService import filename_to_zarr_path, load_file



# File cache
cache = {}

u_list = []

class SignalProcessorNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    endpoints = [
                # 'acquisition_coordinates',
                #  'acquired_spectrum',
                #  'acquisition_finished',
                 'peak_data_request',
                 ]
    
    async def on_acquisition_coordinates(self, data):
        """Initialize acquisition cache with received coordinates

        Parameters
        ----------
        data : dict
            keys: 'mz' and 'time'
        """
        global cache

        value = data['value']
        filename_base = value.get('filename')
        print("Start acquiring sample: %s" %filename_base)
        
        # Cache raw signal in memory
        mz = np.frombuffer( value['mz'], dtype=np.float32 )
        t_range = value['t_range']
        mz_range = [ float(mz[0]), float(mz[-1]) ]

        signal_array = ExtendableDataArray(array_module=da, persist=True)
        signal_array.init_array(dims=('mz', 'time'),
                                coords=[mz, []],
                                name='signal'
                                )
        period_array = ExtendableDataArray(array_module=da, persist=True)
        period_array.init_array(dims=('time'),
                                coords=[[]],
                                name='signal_period'
                                )
        # Collect attributes
        attributes = {'filename': filename_base,
                      'length': float(t_range[1]),
                      'range': mz_range,
                      }
        # Put to cache
        cache_item_dict = {'signal': signal_array,
                           'signal_period': period_array,
                           'attrs': attributes,
                           }

        # TODO: # Initialize arrays for processed signal to write to disk
        # filename_viz = filename_to_zarr_path(filename_base, viz_type)
        # viz_array = ExtendableDataArray(path=filename_viz,
        #                                 array_module=np,
        #                                 dtype=object,
        #                                 chunk_size=1,
        #                                 )
        # viz_array.init_array(dims=('time',),
        #                         coords=[[]],
        #                         name=viz_type
        #                         )
        # viz_period = viz_type + '_period'
        # filename_viz_period = filename_to_zarr_path(filename_base, viz_period)
        # viz_period_array = ExtendableDataArray(path=filename_viz_period,
        #                                         array_module=np,
        #                                         dtype=object,
        #                                         chunk_size=1,
        #                                         )


        cache_item = AttrDict(cache_item_dict)
        cache[filename_base] = cache_item

        global u_list
        global feeder
        global collector

        mz = np.frombuffer( data.get('mz'), dtype=np.float32 )
        feeder.preprocessor.fit(mz, u_list)
        #collector.processor.fit(feeder.preprocessor.borders)

    async def on_acquired_spectrum(self, data):
        """Receive new spectrum, add to cache

        Parameters
        ----------
        data : dict
            keys: 'filename', 'i', 't', 'spec', 'period', ('mz')
        """
        global cache

        value = data['value']
        filename_base = value['filename']

        ti = np.array( [value['t']], dtype=np.float32 )
        period = np.array( [value['period']], dtype=np.float32 )
        print(ti.item())
        spec = np.frombuffer(value['spec'], dtype=np.float32)
        spec = spec.reshape(-1, 1)

        # Get data arrays from cache
        signal_array = cache[filename_base].signal
        period_array = cache[filename_base].signal_period

        if 'mz' in value:
            # mz coordinates provided with data (Orbitrap)
            mz = np.frombuffer(value['mz'], dtype=np.float32)
            mz = mz.reshape(-1,)
        else:
            # Use mz coordinates from signal_array (TOF)
            mz = signal_array.mz

        # Extend data arrays (write to file)
        signal_array.extend_array(spec,
                                  [mz, ti],
                                  'time'
                                  )
        period_array.extend_array(period,
                                  [ti],
                                  'time'
                                  )
        
    async def on_acquisition_finished(self, data):
        """Acquisition finished, feed poison pill to KFeeder        
        """
        value = data['value']
        filename_base = value['filename']
        global feeder
        feeder.queue_in.put(None)

    async def on_peak_data_request(self, data):
        self.log(data)
        value = data['value']
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        
        filename = value['filename']
        mz_range = value.get('mz_range')
        t_range = value.get('t_range')

        min_peak_height = value.get('peak_threshold', 1e-1)
        min_peak_distance = value.get('peak_separation', 3)
        min_peak_width = value.get('peak_width', 3)

        # Check if file is cached
        cache_item = cache.get(filename, None)
        if not cache_item:
            # File not in cache, load
            print("Loading file: %s" %filename)
            cache_item = load_file(filename) # TODO: Load a subset of arrays from file
            cache[filename] = cache_item

        if mz_range is None:
            # Full mz range
            mz_range = cache_item.attrs['range']
            
        if t_range is None:
            # Full time range
            t_range = [0, cache_item.attrs['length']]

        sum_spectrum = cache_item.signal.sel(
                            mz=slice(*mz_range)
                            ).sum(dim='time').compute()

        peak_ind, peak_props = find_peaks(sum_spectrum,
                                          height=min_peak_height,
                                          distance=min_peak_distance,
                                          width=min_peak_width
                                          )
        peak_mz = sum_spectrum.mz[peak_ind].values.astype(np.float32)
        peak_hei = peak_props['peak_heights'].astype(np.float32)

        peak_data = {
                'mz': peak_mz.tobytes(),
                'height': peak_hei.tobytes()
                }

        await self.emit_client_notification('peak_data',
                                            peak_data,
                                            room=client_room
                                            )

async def initialize_feeder():
    global feeder
    global process_q
    
    feeder = KFeeder(queue_out=process_q,
                     # barrier=Barrier(2)
                     )
    feeder.start()

async def initialize_encoders(process_q,
                              results_q,
                              n_jobs=cpu_count(),
                              alpha=Value('d', 1e-3),
                              error_log=False
                              ):
    """Initialize KEncoder processes

    Parameters
    ----------
    process_q : Queue 
        Queue for segments to be processed
    code_q : Queue
        Queue for KEncoder results
    n_jobs : int, optional
        Number of processes to initialize, by default the number
        of available CPU cores as returned by multiprocessing.cpu_count()
    alpha : multiprocessing.Value
        SparseCoder regularization parameter
    error_log : bool, optional
        Log KEncoder errors to txt files, by default False

    Returns
    -------
    encoders : list of KEncoder
        KEncoder process instances
    active_events : list of Event
        List of Event objects, one per KEncoder indicating whether
        they are currently processing an acquisition.
    """
    
    global encoders
    global encoder_active_events
    global D_file    
    
    print("Initializing workers...")
    
    # Load peak dictionary
    D = load_peak_dict(D_file) # scipy.sparse.csr_matrix
    # Make a RawArray of the dictionary D so that encoders can
    # access it without the need to copy whole dictionary for
    # each process
    D_data = RawArray('d', D.data)
    D_indices = RawArray('i', D.indices)
    D_indptr = RawArray('i', D.indptr)
    
    # Initialize n_jobs KEncoders    
    if n_jobs == -1:
        n_jobs = cpu_count()
    for _ in range(n_jobs):
        encoder_active = Event()
        # KEncoder process
        enc = KEncoder(alpha,
                       process_q,
                       results_q,
                       encoder_active,
                       D.shape,
                       D_data,
                       D_indices,   
                       D_indptr,
                       error_log=error_log
                       )
        encoders.append(enc)
        encoder_active_events.append(encoder_active)
    # Start encoders
    for i, enc in enumerate(encoders):
        print("Spawning worker %s/%s" %((i+1), n_jobs))
        enc.start()
        
async def initialize_collector():
    global collector
    global results_q
    
    collector = KCollector(results_q)
    collector.start()



class SignalProcessorClient(BaseServiceClient):
    pass
    # async def init_service(self):
    #     u_list = []
    #     u_list = range(200, 220)
    #     # peaklist = '.\\resources\\xplpar.db'
    #     D_file = '.\\py_code\\resources\\test.h5'

    #     feeder = None
    #     forwarder = None
    #     collector = None
    #     n_jobs = cpu_count()
    #     encoders = [] # Processes
    #     encoder_active_events = [] # Process active 
    #     process_q = Queue()
    #     results_q = Queue()

    # async def service_main(self):
    #     global results_q
    #     global sio
        
    #     while True:
    #         try:
    #             data = results_q.get_nowait()
    #         except Empty:
    #             await asyncio.sleep(.1)
    #             continue
    #         # Received results
    #         if data:
    #             # self.processor.transform(data)
    #             specis = data.get('specis')
    #             u = data.get('u')
    #             # snos = data.get('snos').astype(np.float32).tobytes()
    #             # spec = data.get('spec').astype(np.float32).tobytes()
    #             # approx = data.get('approx').astype(np.float32).tobytes()
    #             # code = data.get('code').astype(np.float32).tobytes()
    #             # peaks = data.get('peaks')
    #             await emit_client_notification('processed_segment',
    #                                            {'specis': specis,
    #                                             'u': u,
    #                                             #'snos': snos,
    #                                             #'spec': spec,
    #                                             #'approx': approx,
    #                                             #'code': code,
    #                                             #'peaks': peaks
    #                                             },
    #                                            no_data_logging=True
    #                                            )
    #         # Received poison pill
    #         else:
    #             # Got None
    #             if data is None:
    #                 # TODO: Currently None should never be received
    #                 pass
    #             else:
    #                 # TODO: Currently False is never received
    #                 break


def run():
    args = parse_cmd_args()       

    # if args['ns'] == '/':
    #     print("SignalProcessorService must be in a private namespace. " +
    #           "Please restart the service with --ns option."
    #           )
    #     return
    
    client = SignalProcessorClient(
                        args['url'],
                        args['port'],
                        (args['ns'], SignalProcessorNamespace)
                        )
        
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run())

    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        print(f"KeyboardInterrupt for {client.__class__.__name__}")
    except Exception as e:
        print(f"Exception '{str(e)}' for {client.__class__.__name__}")
    finally:
        print(f'Service stopped.')


if __name__=='__main__':
    run()