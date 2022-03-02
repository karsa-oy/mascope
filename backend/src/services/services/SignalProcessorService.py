import asyncio

import numpy as np

from scipy.signal import find_peaks

from scipy.signal._peak_finding import (
    # _arg_wlen_as_expected,
    _select_by_property,
    # _unpack_condition_args,
    )

from scipy.signal._peak_finding_utils import (
    _select_by_peak_distance,
    # _peak_prominences,
    # _peak_widths
)

from karsatof.lib.TwTool import TwMassCalibrate, TwTof2Mass
from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.logging import Logger
from karsalib.util import parse_cmd_args
from scenthound.karsavlm.msAlign import find_vlm
from scenthound.kfeeder import KFeeder, FeederProcessor
from scenthound.kworker import KEncoder
from scenthound.kcollector import KCollector

from services.FileIoService import (get_zarr_var_shape,
                                    load_file,
                                    update_props,
                                    update_zarr_array_coord,
                                    zarr_sdk,
                                    )


# File cache
cache = {}

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

    async def on_workspace_sample_peak_list_request(self, data):
        value = data['value']
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        
        filename = value['filename']
        mz_range = value.get('mzRange')
        t_range = value.get('tRange')

        peak_threshold = value.get('parameters', {}).get('minPeakIntensity', None)
        min_peak_distance = value.get('parameters', {}).get('minPeakSeparation', None)
        # min_peak_width = value.get('parameters', {}).get('minPeakWidth', 3)

        # Check if file is cached
        cache_item = cache.get(filename, None)
        if not cache_item:
            # File not in cache, load
            print("Loading file: %s" %filename)
            cache_item = load_file(filename, vars=['peaks'])
            cache[filename] = cache_item

        if 'peaks' not in cache_item:
            # Find peaks and write to file
            cache_item = find_and_write_peaks(cache_item)
            cache[filename] = cache_item

        if mz_range is None:
            # Full mz range
            mz_range = cache_item.attrs['props']['range']
            
        if t_range is None:
            # Full time range
            t_range = [0, cache_item.attrs['props']['length']]
        
        # Add integer index (MS sample bin)
        cache_item = cache_item.assign_coords(
                            tof=('mz', np.arange(len(cache_item.mz)))
                            )

        filtered_peaks = filter_peaks(cache_item,
                                      mz_range,
                                      t_range,
                                      height=peak_threshold,
                                      distance=min_peak_distance
                                      )

        MAX_NO_PEAKS = 20000
        if len(filtered_peaks) > MAX_NO_PEAKS:
            await self.parent.push_log.error(
                        "Warning! Max number of peaks exceeded: %s. \
                        Peak data omitted." %len(filtered_peaks),
                        room=client_room,
                        namespace='/'
                        )
            return

        peak_mzs = filtered_peaks.mz.values
        peak_heights = filtered_peaks.sum(dim='time').values
        peak_tofs = filtered_peaks.tof.values

        await self.emit_client_notification(
            'workspace_sample_response', {
                'type': 'peak-list',
                'requestId': value['requestId'],
                'payload': {
                    'sampleItemId': value['sampleItemId'],
                    'mzsBytes': peak_mzs.astype(np.float32).tobytes(),
                    'heightsBytes': peak_heights.astype(np.float32).tobytes(),
                    'tofsBytes': peak_tofs.astype(np.float32).tobytes()
                }
            },
            room=client_room
            )

def find_and_write_peaks(cache_item):
    if 'signal' not in cache_item:
        # Signal not in cache, load
        cache_item = load_file(cache_item.props['filename'],
                               vars=['signal'],
                               prev_dataset=cache_item
                               )

    sum_spectrum = cache_item.signal.sum(dim='time').compute()
    # Interpolate NaNs for smoothing
    sum_spectrum = sum_spectrum.interpolate_na(dim='mz',
                                               method='linear',
                                               limit=None,
                                               max_gap=2,
                                               )
    peaks, peak_props = find_peaks(sum_spectrum,
                                   height=0,
                                   distance=None,
                                   width=None
                                   )
                                   
    # peak_mz = sum_spectrum.mz[peaks].values.astype(np.float32)
    # peak_heights = peak_props['peak_heights'].astype(np.float32)
    peak_profiles = cache_item.signal[peaks].astype(np.float32)

    zarr_sdk.write_peak_dataset(peak_profiles, cache_item)

    cache_item = load_file(cache_item.props['filename'],
                           vars=['peaks'],
                           prev_dataset=cache_item
                           )
    return cache_item

def filter_peaks(cache_item,
                 mz_range,
                 t_range,
                 height=None,
                 distance=None,
                 prominence=None,
                 width=None
                 ):

    peaks = cache_item.peaks.sel(mz=slice(*mz_range),
                                 time=slice(*t_range)
                                 )
    peaks = peaks.dropna(dim='mz')
    peak_heights = peaks.sum(dim='time').values
    # peak_properties = {'peak_heights': peak_heights}

    keep = np.array([True]*len(peaks))

    if height is not None:
        # peak_heights = peak_properties['peak_heights']
        # Evaluate height condition
        keep_height = peak_heights > height
        keep = np.logical_and(keep, keep_height)
        # peak_properties = {key: array[keep]
        #                    for key, array in peak_properties.items()
        #                    }
    
    if distance is not None:
        # peak_heights = peak_properties['peak_heights']
        # Evaluate distance condition
        keep_distance = _select_by_peak_distance(
                                np.arange(len(peak_heights), dtype=np.intp),
                                peak_heights.astype(np.float64),
                                distance
                                )
        keep = np.logical_and(keep, keep_distance)
        # peak_properties = {key: array[keep]
        #                    for key, array in peak_properties.items()
        #                    }
    
    if prominence is not None or width is not None:
        raise NotImplementedError("Filtering based on 'prominence' or 'width' \
                                  not implemented!"
                                  )
        # # Calculate prominence (required for both conditions)
        # wlen = _arg_wlen_as_expected(wlen)
        # properties.update(zip(
        #     ['prominences', 'left_bases', 'right_bases'],
        #     _peak_prominences(signal, peaks, wlen=wlen)
        # ))
    
    # if prominence is not None:
    #     # Evaluate prominence condition
    #     pmin, pmax = _unpack_condition_args(prominence, signal, peaks)
    #     keep = _select_by_property(properties['prominences'], pmin, pmax)
    #     peaks = peaks[keep]
    #     # properties = {key: array[keep] for key, array in properties.items()}
    
    # if width is not None:
    #     # Calculate widths
    #     properties.update(zip(
    #         ['widths', 'width_heights', 'left_ips', 'right_ips'],
    #         _peak_widths(signal, peaks, rel_height, properties['prominences'],
    #                      properties['left_bases'], properties['right_bases'])
    #     ))
    #     # Evaluate width condition
    #     wmin, wmax = _unpack_condition_args(width, signal, peaks)
    #     keep = _select_by_property(properties['widths'], wmin, wmax)
    #     peaks = peaks[keep]
    #     properties = {key: array[keep] for key, array in properties.items()}
        
    return peaks[keep].compute()

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