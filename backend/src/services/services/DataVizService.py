# -*- coding: utf-8 -*-
"""Data Visualization Service

This script runs the data visualization service for Karsa Tarkka TOF system.

Created on Fri Apr 17 11:35:57 2020
"""

import asyncio
import numpy as np

from colorcet import glasbey_hv as colormap

from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.struct import  LRUDict
from karsalib.util import parse_cmd_args

from services.FileIoService import load_coord, load_file


NO_DATA_LOGGING_DEAULT = False
client = None

# Cache for data arrays
cache = LRUDict(10)


class DataVizServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    # ========== UI requests ==========
    async def on_visualization_ion_focus_request(self, data):
        value = data['value']
        client_room = (
            data.get('client_room') or 
            data['cookies']['src_sid'][0]
            )
        filename = value['filename']
        mzs = value.get('mzs', [])
        rel_abus = value.get('relAbus', [])
        t_range = value.get('tRange')
        dmz_ppm = value.get('paramZoomWindow', 500)

        # Check if file is cached
        cache_item = cache.get(filename, None)
        if not cache_item:
            # File not in cache, load
            print("Loading file: %s" %filename)
            cache_item = load_file(filename, vars=['signal', 'peaks'])
            cache[filename] = cache_item
            
        if t_range is None or t_range == [None, None]:
            # Full time range
            t_range = [0, cache_item.props['length']]
            
        cache_item_slice = cache_item.sel(
                                time=slice(*t_range)
                                )
        main_isotope_i = 0
        main_isotope_height = 0
        for i, mz in enumerate(mzs):
            print("{:d}/{:d}: {:3f}".format(i+1, len(mzs), mz))
            spectrum_traces = []
            timeseries_traces = []
            dmz = 1e-6 * dmz_ppm * mz
            mz_range = (mz-dmz, mz+dmz)
            rel_abu = rel_abus[i]

            isotope_slice = cache_item_slice.sel(
                mz=slice(*mz_range)
                ).compute()
            isotope_timeseries = isotope_slice.signal.sel(
                mz=mz, method='nearest'
                )
            isotope_sum_spectrum = isotope_slice.sum(
                dim='time'
                ).compute()
            isotope_height = isotope_sum_spectrum.signal.sel(
                mz=mz, method='nearest'
                )
            # Sum spectrum traces
            sum_spectrum_mz = isotope_sum_spectrum.mz.values.astype(
                np.float32
                )
            sum_spectrum_y = isotope_sum_spectrum.signal.values.astype(
                np.float32
                )
            if i==0:
                # Set signal normalization constant
                main_isotope_height = float(isotope_height)
            isotope_expected_height = (
                main_isotope_height * (rel_abu / rel_abus[main_isotope_i])
                )
            # MS signal trace
            spectrum_traces.append(
                {
                'name': '{:d}'.format(round(mz)),
                'type': 'scatter',
                'mode': 'lines',
                'line': {
                    'color': 'rgb({},{},{})'.format(*colormap[i])
                },
                'fill': 'tozeroy',
                'fillcolor': 'rgba({},{},{}, .3)'.format(*colormap[i]),
                'x': sum_spectrum_mz.tobytes(),
                'y': sum_spectrum_y.tobytes(),
                'xaxis': 'x{:d}'.format(i+1),
                'yaxis': 'y{:d}'.format(i+1),
                }
            )
            # Peak traces (vertical lines)
            peaks = isotope_sum_spectrum.peaks[np.logical_not(
                        isotope_sum_spectrum.peaks.tof.isnull()
                        )]
            for peak in peaks:
                peak_mz = peak.mz.item()
                peak_height = peak.values.item()
                spectrum_traces.append({
                    'name': "{:.4f}".format(peak_mz),
                    'type': 'scatter',
                    'mode': 'lines+markers',
                    'line': {
                        'color': 'rgb({},{},{})'.format(*colormap[i])
                        },
                    'x': [peak_mz, peak_mz],
                    'y': [0, peak_height],
                    'xaxis': 'x{:d}'.format(i+1),
                    'yaxis': 'y{:d}'.format(i+1),
                })
            # Target mz trace (red vertical line)
            spectrum_traces.append(
                {'name': 'target m/z',
                 'type': 'scatter',
                 'mode': 'lines+markers',
                 'line': {
                    'color': 'red'
                    },
                 'x': [float(mz), float(mz)],
                 'y': [0, isotope_expected_height],
                 'xaxis': 'x{:d}'.format(i+1),
                 'yaxis': 'y{:d}'.format(i+1),
                 }
            )
            # Timeseries traces
            timeseries_time = isotope_timeseries.time.values.astype(
                np.float32
                )
            timeseries_y = isotope_timeseries.values.astype(np.float32)
            timeseries_traces.append(
                {'name': '{:.4f}'.format(mz),
                 'type': 'scatter',
                 'mode': 'lines',
                 'line': {
                     'color': 'rgb({},{},{})'.format(*colormap[i])
                 },
                 'x': timeseries_time.tobytes(),
                 'y': timeseries_y.tobytes(),
                 }
            )
            if i==0:
                sum_timeseries = isotope_timeseries
            else:
                sum_timeseries = sum_timeseries + isotope_timeseries

            await self.emit_client_notification(
                'visualization_ion_focus_response',
                {
                    'spectra': spectrum_traces,
                    'profiles': timeseries_traces,
                },
                room=client_room,
                no_data_logging=True,
                )
            # Sleep 0 to let other tasks be scheduled before next iteration
            await asyncio.sleep(0)

        timeseries_time = sum_timeseries.time.values.astype(np.float32)
        timeseries_y = sum_timeseries.values.astype(np.float32)
        timeseries_traces = [
            {'name': 'sum',
             'type': 'scatter',
             'fill': 'tozeroy',
             'fillcolor': 'rgba(255, 255, 255, .3)',
             'line': {
                'color': 'white'
                },
             'x': timeseries_time.tobytes(),
             'y': timeseries_y.tobytes(),
             },
        ]
        await self.emit_client_notification(
                        'visualization_ion_focus_response',
                        {'profiles': timeseries_traces,
                         },
                        room=client_room,
                        no_data_logging=True,
                        )

    async def on_dataset_coord_updated(self, data):
        value = data['value']
        filename = value['filename']
        var = value['var']
        coord_name = value['coord']
        global cache
        cache_item = cache.get(filename)
        if cache_item:
            new_coord = load_coord(filename, var, coord_name)
            cache_item[coord_name] = new_coord


class DataVizServiceClient(BaseServiceClient):
    def __init__(self, url, port, client_namespace_data):
        super().__init__(url, port, client_namespace_data)


def run():
    global client

    args = parse_cmd_args()
    client = DataVizServiceClient(args['url'],
                                  args['port'],
                                  (args['ns'], DataVizServiceNamespace),
                                  )
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        print(f"KeyboardInterrupt for {client.__class__.__name__}")
    except Exception as e:
        print(f"Exception '{str(e)}' for {client.__class__.__name__}")
    finally:
        client.shutdown_event.set()
        


if __name__=='__main__':
    run()
