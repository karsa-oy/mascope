import asyncio
import numpy as np
import pandas as pd

from karsalib.chemistry import get_exact_isotope_mzs, match_mz
from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.util import parse_cmd_args

from services.FileIoService import filename_to_zarr_path, load_file



# File cache
cache = {}


class TargetServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    endpoints = ['identify_peaks',
                 'integrate_target_ions',
                 ]

    async def on_identify_peaks(self, data):
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        value = data['value']
        
        peak_mzs = np.frombuffer(value['peaks']['mz'], dtype=np.float32).astype(float)
        peak_heis = np.frombuffer(value['peaks']['height'], dtype=np.float32).astype(float)
        peak_tofs = np.frombuffer(value['peaks']['tof'], dtype=np.float32).astype(float)
        targets = value['targets']

        mz_tolerance = 10 # ppm
        iso_abu_tolerance = 10 # %
        min_iso_abu = 0.01 # %

        # TODO: Placeholder list for testing, should get ion formulae from value['targets']
        target_ion_formulae = [
            "CHO2-",
            "NO2-",
            "C2H3O2-",
            "NO3-",
            "Br-",
            "C3H5O3-",
            "C7H5O2-",
            "CH2O2Br-",
            "C3H6O3Br-",
            "C6H11O6-",
            "CH2Br3-",
            "C16H31O2-",
            "C17H33O4-",
            "C5H12N4O7Br-",
            "C16H32O2Br-"
            ]
        # //
        # Compute isotopic ratios from target ion formulae
        target_ion_data = [(i, ion_formula, *ion_spectrum)
                           for i, ion_formula in enumerate(target_ion_formulae)
                           for ion_spectrum in get_exact_isotope_mzs(ion_formula).values()
                           ]
        # Convert target ion data into DataFrame
        target_df = pd.DataFrame(target_ion_data,
                                columns=['id', 'ion composition', 'mz', 'relabu']
                                )
        # Find matching targets for found peaks
        match_df = match_peaks_to_targets(peak_mzs, peak_heis, target_df, mz_tolerance)
        id_peak_tofs = []
        for id in match_df['peak id']:
            if not np.isnan(id):
                id_peak_tofs.append(peak_tofs[int(id)])
            else:
                id_peak_tofs.append(None)
        match_df['peak tof'] = id_peak_tofs
        # Calculate isotope ratios and mz errors
        match_df = calculate_target_match_score(match_df)
        # Compare score with thresholds
        identified_ion_ids = filter_target_matches(match_df, mz_tolerance, iso_abu_tolerance, min_iso_abu)
        identified_ion_peaks = [match_df[match_df.id==match_df_id].fillna(value=-1).to_dict(orient='index')
                                for match_df_id in identified_ion_ids
                                ]

        self.log(identified_ion_peaks)

        await self.emit_client_notification('identified_ions',
                                            identified_ion_peaks, # TODO: Which data to return?
                                            room=client_room
                                            )

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



def calculate_target_match_score(match_df):
    """Calculate measured isotope ratios and mz errors

    Parameters
    ----------
    match_df : pandas.DataFrame
        Target ion dataframe with columns for measured 'peak mz' and 'peak height'

    Returns
    -------
    pandas.DataFrame
        Input dataframe with added columns 'rel peak height', 'iso abu error', 'mz error'
    """
    # Calculate isotope ratios and mz errors
    for target_id in np.unique(match_df.id):
        target = match_df[match_df.id == target_id]
        if not target['peak mz'].any():
            # No matching peaks for this target
            continue
        rel_abu = target['peak height'] / target['peak height'].sum()
        iso_abu_err = (target['relabu'] - rel_abu) * target['relabu'] * 1e2
        match_df.loc[target.index, 'rel peak height'] = rel_abu
        match_df.loc[target.index, 'iso abu error'] = iso_abu_err
        
        mz_err_ppm = (target['peak mz'] - target['mz']) / target['peak mz'] * 1e6
        match_df.loc[target.index, 'mz error'] = mz_err_ppm
    return match_df


def filter_target_matches(match_df, mz_tolerance, iso_abu_tolerance, min_iso_abu):
    """Compare target identification score with thresholds given as input arguments,
    Return 'id's of target ions with one or more peaks identified.

    Parameters
    ----------
    match_df : pandas.DataFrame
        Target ion dataframe with columns for calculated 'mz error' and 'iso abu error'
    mz_tolerance : float
        m/z error tolerance in ppm
    iso_abu_tolerance : float
        Isotope relative abundance error tolerance in %
    min_iso_abu : float
        Minimum relative abundance of an isotope to be considered

    Returns
    -------
    list
        List of 'id' field values for identified targets
    """
    target_ids = np.unique(match_df.id)
    identified_ions_mask = [False] * len(target_ids)
    for target_id in target_ids:
        # Test each target against thresholds
        target = match_df[(match_df.id == target_id) &
                            (match_df.relabu >= min_iso_abu) &
                            (np.abs(match_df['mz error']) <= mz_tolerance) &
                            (np.abs(match_df['iso abu error']) <= iso_abu_tolerance)
                            ]
        if len(target):
            #  At least one peak identified for current target
            identified_ions_mask[target_id] = True

    identified_ion_ids = [match_df_ind
                          for i, match_df_ind in enumerate(target_ids)
                            if identified_ions_mask[i]
                          ]
    
    return identified_ion_ids


def match_peaks_to_targets(peak_mzs, peak_heights, target_ion_df, mz_tolerance):
    """Find matching targets for found peaks

    Parameters
    ----------
    peak_mzs : list
        List of found peak m/z values
    peak_heights : list
        List of found peak intensities
    target_ion_df : pandas.DataFrame
        Target ion data
    mz_tolerance : float
        m/z error tolerance when finding matches, in ppm

    Returns
    -------
    pandas.DataFrame
        Input dataframe with added columns for 'peak id', 'peak mz' and 'peak height',
        containing measured values for matched targets, nan where no matching peak was found.

    Raises
    ------
    NotImplementedError
        Case where more than one peak matches the same target not implemented yet.
    """
    # Find matching targets for found peaks
    target_ion_df['peak mz'] = [None]*len(target_ion_df)
    for peak_i, peak_mz in enumerate(peak_mzs):
        match_is, match_mzs = match_mz(peak_mz, target_ion_df.mz, tolerance=mz_tolerance)
        for match_i in match_is:
            if target_ion_df.loc[match_i, 'peak mz'] is not None:
                raise NotImplementedError("Target already has a matching peak")
            target_ion_df.loc[match_i, 'peak id'] = peak_i
            target_ion_df.loc[match_i, 'peak mz'] = peak_mz
            target_ion_df.loc[match_i, 'peak height'] = peak_heights[peak_i]
    return target_ion_df


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