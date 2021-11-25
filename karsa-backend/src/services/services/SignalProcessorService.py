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

from karsalib.chemistry import match_mz
from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.struct import AttrDict, ExtendableDataArray
from karsalib.util import parse_cmd_args
from scenthound.karsavlm.msAlign import find_vlm
from scenthound.kfeeder import KFeeder, FeederProcessor
from scenthound.kworker import KEncoder
from scenthound.kcollector import KCollector
# from scenthond.kpeak import load_peak_dict

from services.FileIoService import load_file, update_zarr_array_coord



# File cache
cache = {}

u_list = []

class SignalProcessorNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    endpoints = [
                 'fit_mz_calib_function',
                 'mz_calibrate_samples',
                 'peak_data_request',
                 ]
    
    async def on_fit_mz_calib_function(self, data):
        value = data['value']

        new_mz = mz_calibrate_tof(value['peak_tofs'],
                                  value['peak_mzs'],
                                  value['exact_mzs'],
                                  int(np.max(value['peak_tofs'])+1) # TODO: nbrSamples
                                  )
        

    async def on_mz_calibrate_samples(self, data):
        self.log(data)
        value = data['value']
        filenames = value['filenames']
        peaklist = value['peaklist']
        parameters = value.get('parameters', {})

        mz_tolerance = parameters.get('mz_tolerance', 20)
        min_peak_height = parameters.get('peak_threshold', 1e-2)
        min_peak_distance = parameters.get('peak_separation', 3)
        min_peak_width = parameters.get('peak_width', 3)

        # Load samples
        samples = []
        peak_lists = []
        for filename in filenames:
            # Check if file is cached
            cache_item = cache.get(filename, None)
            if not cache_item:
                # File not in cache, load
                print("Loading file: %s" %filename)
                cache_item = load_file(filename, vars=['signal']) # TODO: Load a subset of arrays from file
                # cache[filename] = cache_item
                sum_spectrum = cache_item.signal.mean(dim='time').compute()

                peak_ind, peak_props = find_peaks(sum_spectrum,
                                                  height=min_peak_height,
                                                  distance=min_peak_distance,
                                                  width=min_peak_width
                                                  )
                peak_mz = sum_spectrum.mz[peak_ind].values.astype(np.float32)
                samples.append(cache_item)
                peak_lists.append( (peak_ind, peak_mz) )
            await asyncio.sleep(0)

        # Find VLM points
        peak_mz_arrays = list(zip(*peak_lists))[1]
        vlm_mzs, vlm_per_sample = find_vlm(peak_mz_arrays, mz_tolerance*1e-6, None)
        print("Found %s virtual lock-masses" %len(vlm_mzs))
        # Collect VLM peaks of all samples
        vlm_peak_lists = [ [] for _ in range(len(samples)) ]
        for vlm_pts_sample in vlm_per_sample:
            for vlm_pt in vlm_pts_sample:
                sample_ind, peak_i, peak_mz = vlm_pt
                peak_ind = peak_lists[sample_ind][0][peak_i]
                vlm_peak_lists[sample_ind].append( (peak_ind, peak_mz) )
        # Identify VLM points
        match_is, match_mzs = zip(*[match_mz(mz, peaklist, tolerance=mz_tolerance)
                                    for mz in vlm_mzs
                                    ]
                                  )
        # Filter matches
        mask = np.array( [False] * len(vlm_mzs) )
        exact_mzs = []
        exact_mz_i = []
        for i, vlm_mz_matches in enumerate(match_mzs):
            if len(vlm_mz_matches) == 1:
                # Unique match
                mask[i] = True
                exact_mzs.append(vlm_mz_matches[0])
                exact_mz_i.append(match_is[i][0])
        print("Calibration points: %s" %exact_mzs)
        # Mass calibrate
        for i, sample in enumerate(samples):
            print("Calibrating sample: %s" %sample.filename)
            vlm_tofs_sample, vlm_mzs_sample = zip(*vlm_peak_lists[i])
            # Fit mz function and compute new mz coordinates
            new_mz = mz_calibrate_tof(np.array(vlm_tofs_sample)[mask],
                                      np.array(vlm_mzs_sample)[mask],
                                      exact_mzs,
                                      len(sample.mz)
                                      )
            # Write new mz coordinates to file
            update_zarr_array_coord(sample.filename, 'signal', 'mz', new_mz)
            await asyncio.sleep(0)

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
            cache_item = load_file(filename, vars=['signal'])
            cache[filename] = cache_item

        if mz_range is None:
            # Full mz range
            mz_range = cache_item.attrs['props']['range']
            
        if t_range is None:
            # Full time range
            t_range = [0, cache_item.attrs['props']['length']]

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
        peak_ind = peak_ind.astype(np.float32)

        peak_data = {
                'mz': peak_mz.tobytes(),
                'height': peak_hei.tobytes(),
                'tof': peak_ind.tobytes()
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

def mz_calibrate_tof(peak_tof, peak_mz, exact_mz, nbr_tof_samples):
    from karsatof.lib.TwTool import TwMassCalibrate, TwTof2Mass
    # Prepare arguments
    massCalibMode = 2
    nbrPoints = len(peak_tof)
    mass = np.array(exact_mz, dtype=np.double)
    tof = np.array(peak_tof, dtype=np.double)
    weight = np.ones((nbrPoints,)) # TODO: Set weights?
    nbrParams = np.array([3], dtype=np.int)
    p = np.zeros((nbrParams[0],), dtype=np.double)
    legacyA = legacyB = np.array([None], dtype=np.double)
    # Calibrate
    ret = TwMassCalibrate(massCalibMode,
                          nbrPoints,
                          mass,
                          tof,
                          weight,
                          nbrParams,
                          p,
                          legacyA,
                          legacyB
                          )
    new_mz_coord = [TwTof2Mass(tof, massCalibMode, p)
                    for tof in range(nbr_tof_samples)
                    ]

    new_peak_mz = [ new_mz_coord[p] for p in peak_tof ]
    pre_dmz = mass - peak_mz
    post_dmz = mass - new_peak_mz
    pre_dmz_norm = np.linalg.norm(pre_dmz)
    post_dmz_norm = np.linalg.norm(post_dmz)

    print("dmz norm pre-calib: %.4f, post_calib: %.4f"
          %(pre_dmz_norm, post_dmz_norm)
          )

    return new_mz_coord


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