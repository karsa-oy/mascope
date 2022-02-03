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

from karsatof.lib.TwTool import TwMassCalibrate, TwTof2Mass
from karsalib.chemistry import match_mz
from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.logging import Logger
from karsalib.util import parse_cmd_args
from scenthound.karsavlm.msAlign import find_vlm
from scenthound.kfeeder import KFeeder, FeederProcessor
from scenthound.kworker import KEncoder
from scenthound.kcollector import KCollector
# from scenthond.kpeak import load_peak_dict

from services.FileIoService import (get_zarr_var_shape,
                                    load_file,
                                    update_props,
                                    update_zarr_array_coord
                                    )



# File cache
cache = {}

u_list = []

class SignalProcessorNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    async def on_fit_mz_calib_function(self, data):
        value = data['value']
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]

        mz_calib, stats = mz_calibrate_tof(value['peak_tofs'],
                                         value['peak_mzs'],
                                         value['exact_mzs'],
                                         int(np.max(value['peak_tofs'])+1) # TODO: nbrSamples
                                         )
        await self.emit_client_notification('mz_calibration',
                                            {'fit': mz_calib,
                                             'stats':
                                                {'mz': stats['mz'].astype(np.float32).tobytes(),
                                                 'pre_dmz': stats['pre_dmz'].astype(np.float32).tobytes(),
                                                 'post_dmz': stats['post_dmz'].astype(np.float32).tobytes()
                                                 }
                                            },
                                            room=client_room
                                            )
        
    async def on_mz_calibrate_samples(self, data):
        global cache

        self.log(data)
        value = data['value']
        mode = value['fit']['mode']
        par = value['fit']['par']
        filenames = value['filenames']

        nbr_samples = get_zarr_var_shape(filenames[0], 'signal')[0]

        par = np.array(par, dtype=np.double)
        new_mz = np.array([TwTof2Mass(tof, mode, par)
                           for tof in range(nbr_samples)
                           ])
        new_range = [new_mz[0], new_mz[-1]]

        for filename in filenames:
            self.log("Calibrating file: %s" %filename)
            if nbr_samples != get_zarr_var_shape(filename, 'signal')[0]:
                raise Exception("Number of TOF samples does not match")
            # Write new mz coordinates to file
            update_zarr_array_coord(filename, 'signal', 'mz', new_mz)
            update_props(filename, {'range': new_range})
            cache_item = cache.get(filename)
            if cache_item:
                cache_item['mz'] = new_mz
                cache_item.attrs['props'].update({'range': new_range})
                cache[filename] = cache_item
            await self.emit_client_notification('dataset_coord_updated',
                                                {'filename': filename,
                                                 'coord': 'mz',
                                                 'var': 'signal'
                                                 }
                                                )

    async def on_peak_data_request(self, data):
        value = data['value']
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        
        filename = value['filename']
        mz_range = value.get('mz_range')
        t_range = value.get('t_range')

        peak_threshold = value.get('parameters', {}).get('peak_threshold', 5)*1e-2 # [%]
        min_peak_distance = value.get('parameters', {}).get('peak_separation', 3)
        min_peak_width = value.get('parameters', {}).get('peak_width', 3)

        # Check if file is cached
        cache_item = cache.get(filename, None)
        if not cache_item:
            # File not in cache, load
            print("Loading file: %s" %filename)
            cache_item = load_file(filename, vars=['signal']) #vars=['centroids', 'signal'])
            cache[filename] = cache_item

        if mz_range is None:
            # Full mz range
            mz_range = cache_item.attrs['props']['range']
            
        if t_range is None:
            # Full time range
            t_range = [0, cache_item.attrs['props']['length']]

        # If centroid data saved, use it
        if False:#'centroids' in cache_item:
            sum_centroids = cache_item.centroids.sel(
                                mz=slice(*mz_range),
                                time=slice(*t_range)
                                ).sum(dim='time').compute()
            min_peak_height = peak_threshold * sum_centroids.max().compute().item()
            ind = (sum_centroids > min_peak_height).compute()
            peak_mz = sum_centroids.mz[ind].load()
            peak_hei = sum_centroids[ind].load()
            peak_mz = peak_mz.values.astype(np.float32)
            peak_hei = peak_hei.values.astype(np.float32)
            peak_ind = np.array(range(len(peak_mz))).astype(np.float32)
        # Find peaks
        else:
            sum_spectrum = cache_item.signal.sel(
                                mz=slice(*mz_range),
                                time=slice(*t_range)
                                ).sum(dim='time').compute()
            # Interpolate NaNs for smoothing
            sum_spectrum = sum_spectrum.interpolate_na(dim='mz',
                                                       method='linear',
                                                       limit=None,
                                                       max_gap=2,
                                                       )
            min_peak_height = peak_threshold * sum_spectrum.max().compute().item()
            peak_ind, peak_props = find_peaks(sum_spectrum,
                                            height=min_peak_height,
                                            distance=min_peak_distance,
                                            width=min_peak_width
                                            )
            peak_mz = sum_spectrum.mz[peak_ind].values.astype(np.float32)
            peak_hei = peak_props['peak_heights'].astype(np.float32)
            peak_ind = peak_ind.astype(np.float32)

        MAX_NO_PEAKS = 20000
        if len(peak_mz) > MAX_NO_PEAKS:
            await self.parent.push_log.error(
                        "Warning! Max number of peaks exceeded: %s. Peak data omitted." %len(peak_mz),
                        room=client_room,
                        namespace='/'
                        )
            return

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
    # Prepare arguments
    mass_calib_mode = 2
    nbr_points = len(peak_tof)
    mass = np.array(exact_mz, dtype=np.double)
    sind = np.argsort(mass)
    tofs = np.array(peak_tof, dtype=np.double)
    mass = mass[sind]
    tofs = tofs[sind]
    peak_mz = np.array(peak_mz)[sind]
    weight = np.ones((nbr_points,)) # TODO: Set weights?
    nbr_params = np.array([3], dtype=np.int)
    mass_calib_par = np.zeros((nbr_params[0],), dtype=np.double)
    legacy_a = legacy_b = np.array([None], dtype=np.double)
    # Calibrate
    ret = TwMassCalibrate(mass_calib_mode,
                          nbr_points,
                          mass,
                          tofs,
                          weight,
                          nbr_params,
                          mass_calib_par,
                          legacy_a,
                          legacy_b
                          )
    
    if ret != 4:
        raise Exception("TwMassCalibrate failed with code: %s" %ret)

    mass_calib = {'mode': mass_calib_mode,
                  'par': list(mass_calib_par)
                  }

    # new_mz_coord = [TwTof2Mass(tof, massCalibMode, p)
    #                 for tof in range(nbr_tof_samples)
    #                 ]

    new_peak_mz = np.array([TwTof2Mass(tof, mass_calib_mode, mass_calib_par)
                            for tof in tofs
                            ])
    pre_dmz = (mass - peak_mz) / mass * 1e6
    post_dmz = (mass - new_peak_mz) / mass * 1e6
    pre_dmz_norm = np.linalg.norm(pre_dmz)
    post_dmz_norm = np.linalg.norm(post_dmz)

    stats = {
        'mz': mass,
        'pre_dmz': pre_dmz,
        'post_dmz': post_dmz,
        'per_dmz_norm': pre_dmz_norm,
        'post_dmz_norm': post_dmz_norm
    }

    return mass_calib, stats


class SignalProcessorClient(BaseServiceClient):
    async def init_service(self):
        self.push_log = Logger(self.__class__.__name__, f_log_level=None)
        self.push_log.configure_notifications(sender=self.ns_handler)
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