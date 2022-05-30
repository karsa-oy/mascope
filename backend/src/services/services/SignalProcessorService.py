import asyncio

import json
import numpy as np


from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.logging import Logger
from karsalib.peak import mz_calibrate_tof
from karsalib.util import parse_cmd_args

from karsatof.lib.TwTool import TwTof2Mass
from karsatof.kgenerator import remove_duplicate_mz_values


from services.FileIoService import (
    get_zarr_var_shape,
    load_coord,
    update_props,
    update_zarr_array_coord,
)


# File cache
cache = {}

class SignalProcessorNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    async def on_calibration_mz_fit_request(self, data):
        value = data['value']
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]

        mz_calib, stats = mz_calibrate_tof(
            value['peakTofs'],
            value['peakMzs'],
            value['exactMzs']
            )
        await self.emit_client_notification(
            'calibration_mz_fit_response', {
                'fit': mz_calib,
                'stats': {
                    'postMz': stats['new_mz'].astype(np.float32).tobytes(),
                    'postDmz': stats['post_dmz'].astype(np.float32).tobytes(),
                    'postDmzNorm': stats['post_dmz_norm'],
                    'preDmzNorm': stats['pre_dmz_norm'],
                }
            },
            room=client_room
            )
        
    async def on_calibration_mz_apply_request(self, data):
        global cache

        value = data['value']
        mode = value['fit']['mode']
        par = value['fit']['par']
        filenames = value['filenames']

        nbr_samples = get_zarr_var_shape(filenames[0], 'signal')[0]

        par = np.array(par, dtype=np.double)
        new_mz = np.array([
            TwTof2Mass(tof, mode, par)
            for tof in range(nbr_samples)
        ])
        new_mz = remove_duplicate_mz_values(new_mz)
        new_range = [new_mz[0], new_mz[-1]]

        for filename in filenames:
            self.log("Calibrating file: %s" %filename)
            if nbr_samples != get_zarr_var_shape(filename, 'signal')[0]:
                raise Exception("Number of TOF samples does not match")
            # Write new mz coordinates to file
            update_zarr_array_coord(filename, 'signal', 'mz', new_mz)
            peak_tofs = load_coord(filename, 'peaks', 'tof')
            new_peak_mzs = new_mz[peak_tofs.astype(int)]
            update_zarr_array_coord(filename, 'peaks', 'mz', new_peak_mzs)
            update_props(filename, {'range': new_range})
            cache_item = cache.get(filename)
            if cache_item:
                cache_item['mz'] = new_mz
                cache_item.attrs['props'].update({'range': new_range})
                cache[filename] = cache_item

            await self.emit_client_notification(
                'dataset_coord_updated', {
                    'filename': filename,
                    'coord': 'mz',
                    'var': 'signal'
                }
            )
            await self.emit_client_notification(
                'sample_file_update_request', {
                    'id': filename,
                    'mz_calibration': value['fit']
                }
            )
            await asyncio.sleep(0)


class SignalProcessorClient(BaseServiceClient):
    async def init_service(self):
        self.push_log = Logger(self.__class__.__name__, f_log_level=None)
        self.push_log.configure_notifications(sender=self.ns_handler)


def run():
    args = parse_cmd_args()       

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