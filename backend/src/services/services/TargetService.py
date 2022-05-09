import asyncio
import numpy as np
import pandas as pd

from karsalib.peak import detect_peaks, filter_peaks
from karsalib.match import identify_matches, calculate_match_stats

from karsalib.molmass import Formula
from karsalib.chemistry import get_exact_isotope_mzs
from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.util import parse_cmd_args

from services.FileIoService import load_file


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
            if not compound.get('formula'):
                continue
            for ionization_mechanism in ionization_mechanisms:
                ion_id += 1
                try:
                    # get and save ions
                    ion = Formula('(' +
                        compound['formula'].rstrip() +
                        ionization_mechanism[:-1] +
                        ')' + ionization_mechanism[-1]
                    )
                except ValueError:
                    message = f"""
                        {compound['formula']} cannot be ionized by mechanism {ionization_mechanism}
                     """
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
                        
        return {
            'type': 'success',
            'body': {'ions': target_ions, 'isotopes': target_isotopes, 'messages': messages},
        }

    async def on_match_request(self, data):
        client_room = data.get('client_room') or data['cookies']['src_sid'][0]

        value = data['value']
        sample_item = value['sampleItem']
        filename = sample_item['filename']

        # peak parameters
        mz_range = value['mzRange']
        t_range = value['tRange']
        peak_threshold = value['minPeakIntensity']
        min_peak_distance = value['minPeakSeparation']

        # match parameters
        mz_tolerance = value['mzTolerance'] # ppm
        iso_abu_tolerance = value['isoAbuTolerance']/100 # %

        # STEP 1 - Get peaks

        # Check if file is cached
        cache_item = cache.get(filename, None)
        if not cache_item:
            # File not in cache, load
            print("Loading file: %s" %filename)
            cache_item = load_file(filename, vars=['peaks'])
            cache[filename] = cache_item

        if 'peaks' not in cache_item:
            # Find peaks and write to file
            cache_item = detect_peaks(cache_item)
            cache[filename] = cache_item

        if mz_range is None:
            # Full mz range
            mz_range = cache_item.attrs['props']['range']
            
        if t_range is None:
            # Full time range
            t_range = [0, cache_item.attrs['props']['length']]

        filtered_peaks = filter_peaks(
            cache_item,
            mz_range,
            t_range,
            height=peak_threshold,
            distance=min_peak_distance
        )

        MAX_NO_PEAKS = 20000
        if len(filtered_peaks) > MAX_NO_PEAKS:
            await self.parent.push_log.error("""
                    Warning! Max number of peaks exceeded: %s.
                    Peak data omitted.
                """ %len(filtered_peaks),
                room=client_room,
                namespace='/'
            )
            return

        # STEP 2 - Perform matching

        # parse peak data
        peak_mzs = filtered_peaks.mz.values
        peak_heights = filtered_peaks.sum(dim='time').values
        peak_tofs = filtered_peaks.tof.values

        # load target isotopes 
        target_isotope_df = pd.DataFrame \
            .from_dict(value['targetIsotopes']) \
            .rename(columns={
                'id': 'targetIsotopeId',
                'ionId': 'targetIonId',
                'compoundId': 'targetCompoundId'
            })

        # match peaks to isotopes
        isotope_match_df = identify_matches(
            peak_mzs,
            peak_heights,
            target_isotope_df,
            mz_tolerance
        )

        if len(isotope_match_df) > 0:
            # append peak TOFs
            match_tofs = []
            for peak_id in isotope_match_df['samplePeakId']:
                if not np.isnan(peak_id):
                    match_tofs.append(peak_tofs[int(peak_id)])
                else:
                    match_tofs.append(None)
            isotope_match_df.loc[:, 'samplePeakTof'] = match_tofs

            # calculate ion and compound target match scores
            return {
                'type': 'success',
                'body': {
                    'matches': calculate_match_stats(
                        isotope_match_df,
                        sample_item,
                        iso_abu_tolerance,
                        mz_tolerance
                    ),
                    'sampleItems': [sample_item]
                }
            }
        else:
            return None


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