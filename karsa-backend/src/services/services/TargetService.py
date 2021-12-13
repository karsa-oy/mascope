import asyncio
import numpy as np
import pandas as pd

from karsalib.molmass import Formula
from karsalib.chemistry import get_exact_isotope_mzs, match_mz
from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.util import parse_cmd_args

from services.FileIoService import filename_to_zarr_path, load_file


# File cache
cache = {}

class TargetServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    endpoints = [
        'compute_target_ions',
        'identify_peaks',
        ]

    async def on_compute_target_ions(self, data):
        value = data['value']
        # self.log(data)
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        
        compounds = value['compounds']
        ionization_mechanisms = value['ionization_mechanism'].split(',')

        target_ions = []
        for compound_id, compound in enumerate(compounds):
            for ionization_mechanism in ionization_mechanisms:
                ion_formula = Formula('(' +
                                      compound +
                                      ionization_mechanism[:-1] +
                                      ')' +
                                      ionization_mechanism[-1]
                                      )
                ion_charge = ion_formula.charge
                if ion_charge == -1:
                    charge_string = "-"
                elif ion_charge == +1:
                    charge_string = "+"
                else:
                    charge_string = ""
                ion_string = ion_formula.formula + charge_string
                target_ions.append((compound_id, ion_string))

        # Compute isotopic ratios from target ion formulae
        target_ion_data = [(compound_id, ion_id, ion_formula, *ion_spectrum)
                           for ion_id, (compound_id, ion_formula) in enumerate(target_ions)
                           for ion_spectrum in get_exact_isotope_mzs(ion_formula).values()
                           ]
        # Convert target ion data into DataFrame
        target_df = pd.DataFrame(target_ion_data,
                                 columns=['target id', 'ion id', 'ion composition', 'mz', 'rel abu']
                                 )

        await self.emit_client_notification('target_ions',
                                            list( target_df.to_dict(orient='index').values() ),
                                            room=client_room
                                            )

    async def on_identify_peaks(self, data):
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        value = data['value']
        
        peak_mzs = np.frombuffer(value['peaks']['mz'], dtype=np.float32).astype(float)
        peak_heis = np.frombuffer(value['peaks']['height'], dtype=np.float32).astype(float)
        peak_tofs = np.frombuffer(value['peaks']['tof'], dtype=np.float32).astype(float)
        target_ion_data = value['target_ions']
        target_df = pd.DataFrame.from_dict(target_ion_data)

        # Parameters
        mz_tolerance = value.get('parameters', {}).get('mz_tolerance', 10) # ppm
        iso_abu_tolerance = value.get('parameters', {}).get('iso_abu_tolerance', 10) # %
        min_iso_abu = value.get('parameters', {}).get('min_iso_abu', 1) / 100.0 # frac

        # Filter by minimum isotope abundance
        target_df = target_df[(target_df['rel abu'] >= min_iso_abu)]

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
        # Filter by isotope abundance error tolerance
        match_df = match_df[(np.abs(match_df['iso abu error']) <= iso_abu_tolerance)]

        identified_ion_peaks = match_df
        identified_ion_peaks = identified_ion_peaks.dropna(subset=['peak mz'])
        self.log(identified_ion_peaks)

        await self.emit_client_notification('identified_ions',
                                            identified_ion_peaks.to_dict(orient='index'),
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
    match_df['rel peak height'] = [np.nan]*len(match_df)
    match_df['iso abu error'] = [np.nan]*len(match_df)
    match_df['mz error'] = [np.nan]*len(match_df)
    # Calculate isotope ratios and mz errors
    for target_id in np.unique(match_df['ion id']):
        target = match_df[match_df['ion id'] == target_id]
        if not target['peak mz'].any():
            # No matching peaks for this target
            continue
        rel_abu = target['peak height'] / target['peak height'].sum()
        iso_abu_err = (rel_abu - target['rel abu']) * target['rel abu'] * 1e2
        match_df.loc[target.index, 'rel peak height'] = rel_abu
        match_df.loc[target.index, 'iso abu error'] = iso_abu_err
        
        mz_err_ppm = (target['peak mz'] - target['mz']) / target['peak mz'] * 1e6
        match_df.loc[target.index, 'mz error'] = mz_err_ppm
    return match_df

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
    target_ion_df['peak id'] = [np.nan]*len(target_ion_df)
    target_ion_df['peak mz'] = [np.nan]*len(target_ion_df)
    target_ion_df['peak height'] = [np.nan]*len(target_ion_df)
    target_ion_df = target_ion_df.sort_values('mz')

    for peak_i, peak_mz in enumerate(peak_mzs):
        match_is, match_mzs = match_mz(peak_mz, list(target_ion_df.mz), tolerance=mz_tolerance)
        for match_i in match_is:
            target_mz = target_ion_df.iloc[match_i]['mz']
            # print("Found match for target mz %.4f: peak mz %.4f" %(target_mz, peak_mz))
            if not np.isnan(target_ion_df.iloc[match_i]['peak mz']):
                prev_peak_mz = target_ion_df.iloc[match_i]['peak mz']
                prev_peak_mz_err = np.abs(prev_peak_mz - target_mz)
                curr_peak_mz_err = np.abs(peak_mz - target_mz)
                # print("Found match for target mz %.4f: peak mz %.4f" %(target_mz, peak_mz))
                if prev_peak_mz_err < curr_peak_mz_err:
                    # print("For target mz %.4f replacing peak %.4f with %.4f" %(target_mz, prev_peak_mz, peak_mz))
                    # Closer match has been found already
                    continue
            target_ion_index = target_ion_df.index[match_i]
            target_ion_df.loc[target_ion_index, 'peak id'] = peak_i
            target_ion_df.loc[target_ion_index, 'peak mz'] = peak_mz
            target_ion_df.loc[target_ion_index, 'peak height'] = peak_heights[peak_i]

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