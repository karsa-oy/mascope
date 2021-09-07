import asyncio
import numpy as np


from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.util import parse_cmd_args

from services.FileIoService import filename_to_zarr_path, load_file



# File cache
cache = {}


class TargetServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    endpoints = ['integrate_target_ions',
                 ]

    async def on_integrate_target_ions(self, data):
        value = data['value']
        self.log(data)
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        
        filename = value['filename']
        mzs = value.get('mz')
        t_range = value.get('t_range')
        # t_resolution = value.get('t_resolution')
        # request_id = value['request_id']

        # Check if file is cached
        cache_item = cache.get(filename, None)
        if not cache_item:
            # File not in cache, load
            print("Loading file: %s" %filename)
            cache_item = load_file(filename) # TODO: Load a subset of arrays from file
            cache[filename] = cache_item
            
        if t_range is None:
            # Full time range
            t_range = [0, cache_item.attrs['length']]

        if not hasattr(mzs, '__iter__'):
            mzs = [mzs]

        # Integrate requested mz range(s)
        intensities = []
        for mz in mzs:
            dmz = 0.1 # TODO: Set window properly
            if mz is not None:
                mz_range = (mz-dmz, mz+dmz)
            else:
                mz_range = (None, None)
            # TODO: Properly integrate instead of sum
            sum_signal = cache_item.signal.sel(
                            mz=slice(*mz_range)
                            ).sum(dim='time').sum(dim='mz').compute().item()
            intensities.append(sum_signal)

        await self.emit_client_notification('target_ion_intensities',
                                            intensities,
                                            room=client_room
                                            )



class TargetServiceClient(BaseServiceClient):
    pass


def run():
    args = parse_cmd_args()
    
    client = TargetServiceClient(
                        args['url'],
                        args['port'],
                        (args['ns'], TargetServiceNamespace)
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