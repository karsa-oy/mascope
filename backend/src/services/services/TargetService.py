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

    async def on_target_ion_calculation_request(self, data):
        value = data['value']
        self.log(data)
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]

        compounds = value['compounds']
        ionization_mechanisms = value['ionizationMechanisms']
        min_iso_abu = value['minIsoAbu'] / 100.0

        target_ions = []
        target_isotopes = []
        ion_id = 0
        isotope_id = 0
        messages = []
        for compound in compounds:
            for ionization_mechanism in ionization_mechanisms:
                ion_id += 1
                try:
                    # get and save ions
                    ion = Formula('(' +
                        compound['formula'] +
                        ionization_mechanism[:-1] +
                        ')' + ionization_mechanism[-1]
                    )
                except ValueError:
                    message = f"{compound['formula']} cannot be ionized by mechanism {ionization_mechanism}"
                    self.log(message)
                    messages.append({
                        'level': 'warning',
                        'body': message
                    })
                else:
                    # compute charge
                    ion_charge = ion.charge
                    if ion_charge == -1:
                        charge_string = "-"
                    elif ion_charge == +1:
                        charge_string = "+"
                    else:
                        charge_string = ""
                    # construct ion formula
                    ion_formula = ion.formula + charge_string
                    # construct and save ion row
                    target_ions.append({
                        'id': ion_id,
                        'compoundId': compound['id'],
                        'formula': ion_formula,
                        'ionMech': ionization_mechanism,
                        'charge': ion.charge,
                    })
                    # construct and save isotope rows
                    isotopes = get_exact_isotope_mzs(ion_formula).values()
                    for isotope in isotopes:
                        [mz, rel_abu] = isotope
                        if rel_abu > min_iso_abu:
                            isotope_id += 1
                            target_isotopes.append({
                                'id': isotope_id,
                                'ionId': ion_id,
                                'mz': mz,
                                'relAbu': rel_abu
                            })
                        
        await self.emit_client_notification('target_ion_calculation_response',
                                            {'ions': target_ions, 'isotopes': target_isotopes, 'messages': messages},
                                            room=client_room
                                            )

    async def on_match_request(self, data):
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]
        value = data['value']
        sample_item = value['sampleItem']
        
        # load parameters
        mz_tolerance = value['mzTolerance'] # ppm
        iso_abu_tolerance = value['isoAbuTolerance']/100 # %

        # parse peak data
        parse = lambda val : np.frombuffer(val, dtype=np.float32).astype(float)
        peak_mzs = parse(sample_item['peaks']['mzCol'])
        peak_heights = parse(sample_item['peaks']['heightCol'])
        peak_tofs = parse(sample_item['peaks']['tofCol'])
        
        # load targets 
        target_isotope_data = value['targetIsotopes']
        target_isotope_df = pd.DataFrame.from_dict(target_isotope_data)
        target_isotope_df = target_isotope_df.rename(columns={
            'id': 'targetIsotopeId',
            'ionId': 'targetIonId',
            'compoundId': 'targetCompoundId'
            })


        # match peaks to isotopes
        isotope_match_df = match_sample_peaks_to_target_isotopes(
            peak_mzs, 
            peak_heights, 
            target_isotope_df, 
            mz_tolerance
        )

        # append peak TOFs
        match_tofs = []
        for peak_id in isotope_match_df['samplePeakId']:
            if not np.isnan(peak_id):
                match_tofs.append(peak_tofs[int(peak_id)])
            else:
                match_tofs.append(None)
        isotope_match_df.loc[:, 'samplePeakTof'] = match_tofs

        # calculate ion and compound target match scores
        match_stats = calculate_match_stats(
            isotope_match_df, 
            sample_item, 
            iso_abu_tolerance, 
            mz_tolerance
            )

        match_update = {
            'requestId' : value['requestId'], 
            'matchStats': match_stats
        }

        await self.emit_client_notification('match_update',
                                            match_update,
                                            room=client_room
                                            )


def match_sample_peaks_to_target_isotopes(peak_mzs, peak_heights, target_isotope_df, mz_tolerance):
    """Find matching targets for found peaks

    Parameters
    ----------
    peak_mzs : list
        List of found peak m/z values
    peak_heights : list
        List of found peak intensities
    target_isotope_df : pandas.DataFrame
        Target isotope data
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
    # Initialize match dataframe from target isotope dataframe
    isotope_match_df = target_isotope_df
    isotope_match_df.loc[:, 'samplePeakId'] = np.nan
    isotope_match_df.loc[:, 'samplePeakMz'] = np.nan
    isotope_match_df.loc[:, 'samplePeakHeight'] = np.nan
    peak_sorting = np.argsort(peak_mzs)

    for target_isotope_index, target_isotope_row in isotope_match_df.iterrows():
        target_mz = target_isotope_row.mz
        match_indeces, match_mzs = match_mz(target_mz,
                                       peak_mzs[peak_sorting],
                                       tolerance=mz_tolerance
                                       )
        for match_index in match_indeces:
            peak_index = peak_sorting[match_index]
            peak_mz = peak_mzs[peak_index]
            peak_height = peak_heights[peak_index]
            if not np.isnan(isotope_match_df.loc[target_isotope_index, 'samplePeakId']):
                prev_mz_err = np.abs(isotope_match_df.loc[target_isotope_index, 'samplePeakMz'] - target_mz)
                new_mz_err = np.abs(peak_mz - target_mz)
                if new_mz_err > prev_mz_err:
                    continue
            isotope_match_df.loc[target_isotope_index, 'samplePeakId'] = peak_index
            isotope_match_df.loc[target_isotope_index, 'samplePeakMz'] = peak_mz
            isotope_match_df.loc[target_isotope_index, 'samplePeakHeight'] = peak_height

    isotope_match_df = isotope_match_df.dropna(subset=['samplePeakMz'])

    return isotope_match_df

def calculate_match_stats(isotope_match_df, sample_item, iso_abu_tolerance, mz_tolerance):
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
    isotope_match_df.loc[:, 'relPeakHeight'] = np.nan 
    isotope_match_df.loc[:, 'isoAbuError'] = np.nan
    isotope_match_df.loc[:, 'mzError'] = np.nan
    isotope_match_df.loc[:, 'matchScore'] = np.nan

    # STEP 1 - Select good isotope level matches
        
    # calculate isotope ratios

    # sum matched sample peak heights for each ion
    ion_level_peak_sums = isotope_match_df \
        .groupby(['targetIonId'], as_index=False)['samplePeakHeight'] \
        .sum()

    # join sums back to the isotope level
    isotope_level_peak_sums = pd.merge(
        isotope_match_df, 
        ion_level_peak_sums\
            .rename(columns={'samplePeakHeight': 'samplePeakHeightSum'}),
        on=['targetIonId'], how='outer'
    )

    # compute relative peak heights
    isotope_match_df.loc[:, 'relPeakHeight'] = \
        isotope_match_df['samplePeakHeight'] / isotope_level_peak_sums['samplePeakHeightSum']

    # calculate isotope ratio errors
    isotope_match_df.loc[:, 'isoAbuError'] =  \
        isotope_match_df['relAbu'] * ( isotope_match_df['relPeakHeight'] - isotope_match_df['relAbu'] )

    # select matches based on threshold
    isotope_match_df = isotope_match_df[np.abs(isotope_match_df['isoAbuError']) <= iso_abu_tolerance]

    # STEP 2 - Calculate isotope level stats

    # calculate mz errors
    isotope_match_df.loc[:, 'mzError'] = \
        1e6 * ( isotope_match_df['samplePeakMz'] - isotope_match_df['mz'] ) / isotope_match_df['samplePeakMz']

    # isotope level match score
    isotope_match_df.loc[:, 'matchScore'] = \
        ( 1 - isotope_match_df['isoAbuError'] ) * ( 1 - abs(isotope_match_df['mzError']) / mz_tolerance )
    # append sample id
    isotope_match_df.loc[:, 'sampleItemId'] = sample_item['id']

    # STEP 3 - Calculate ion level stats

    # ion level score is the sum of isotope relative abundances
    ion_match_df = isotope_match_df \
        .groupby(['targetIonId', 'targetCompoundId']) \
        .agg( \
            matchScore = ('relAbu', 'sum'), \
            samplePeakHeight = ('samplePeakHeight', 'sum') \
            ) \
        .reset_index()
    # append sample id
    ion_match_df.loc[:, 'sampleItemId'] = sample_item['id']

    # save ion level peak sums 
    ion_match_df.loc[:, 'samplePeakHeight'] = ion_level_peak_sums

    # STEP 4 - Calculate compound level stats

    # compound level aggregation
    compound_match_df = ion_match_df \
        .groupby(['targetCompoundId']) \
        .agg( \
            matchScore = ('matchScore', 'max'), \
            samplePeakHeight = ('samplePeakHeight', 'sum') \
            ) \
        .reset_index()
    # append sample id
    compound_match_df.loc[:, 'sampleItemId'] = sample_item['id']

    # STEP 5 - Format output

    output = lambda df: list(df.to_dict(orient='index').values())
    match_stats = {
        'isotope': output(isotope_match_df),
        'ion': output(ion_match_df),
        'compound': output(compound_match_df)
    }

    return match_stats

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