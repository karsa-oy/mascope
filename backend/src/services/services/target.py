import asyncio
import numpy as np
import pandas as pd

from karsalib.peak import detect_peaks, filter_peaks
from karsalib.match import identify_matches, calculate_match_stats

from karsalib.molmass import Formula
from karsalib.chemistry import get_exact_isotope_mzs
from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.util import (
    parse_cmd_args,
    get_client_notification_context,
    map_to_snake_case,
    map_to_camel_case
)
from karsalib.struct import LRUDict

from karsalib.db import DbInstance, gen_id, get_ids

from services.file_io import load_file

db = DbInstance()

# File cache
cache = LRUDict(10)


class TargetServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    async def on_dataset_coord_updated(self, data):
        value = data['value']
        filename = value['filename']
        var = value['var']
        coord_name = value['coord']
        global cache
        try:
            cache_item = cache.pop(filename)
        except KeyError:
            pass

    # TARGETS
    # target collections

    async def on_target_collection_create_request(self, data):
        raw_target_collections = map_to_snake_case(data['value'])
        target_collections = [
            {**target_collection, 'id': gen_id()}
            for target_collection in raw_target_collections
        ]
        for target_collection in target_collections:
            # create compounds
            created_compound_ids = (
                await self.on_target_compound_create_request(
                    {'value': target_collection['target_compounds']}
                )
            )['body']['compound'],
            # create collection
            db.target_collection_create(
                id=target_collection['id'],
                name=target_collection['name'],
                description=target_collection['description'],
            )
            # add compounds to collection
            for created_compound_id in created_compound_ids:
                db.target_collection_add_compound(
                    collection_id=target_collection['id'],
                    compound_id=created_compound_id
                )
            # add collection to sample batches
            for sample_batch_id in target_collection['sample_batches']:
                db.target_collection_add_to_sample_batch(
                    target_collection_id=target_collection['id'],
                    sample_batch_id=sample_batch_id,
                )

        target_collection_ids = get_ids(target_collections)
        await self.notify(
            'target_collection_event', {
                'type': 'create', 
                'ids': target_collection_ids
            },
            **{
                **get_client_notification_context(data),
                'room': 'target/collection',
            }
        )
        return {
            'type': 'success',
            'body': target_collection_ids
        }

    async def on_target_collection_read_request(self, data):
        filters = map_to_snake_case(data['value'])
        # get target collection ids linked to sample batch
        sample_batch_id = filters.pop('sample_batch_id')
        target_collection_ids = [
            link['target_collection_id']
            for link in db.target_collection_in_sample_batch.read(
                sample_batch_id=sample_batch_id
            )
        ]
        # read target collections
        target_collections = db.target_collection_read(
            id=target_collection_ids,
            **filters
        )
        return {
            'type': 'success',
            'body': map_to_camel_case(target_collections)
        }

    async def on_target_collection_update_request(self, data):
        target_collections = map_to_snake_case(data['value'])
        for target_collection in target_collections:
            # N.B - instead of updating compounds, we
            # simply create new ones and update the collection
            # record to link to them.
            created_compound_ids = await (
                self.on_target_compound_create_request(
                    target_collection['compounds']
                )['body']['compound']
            )
            db.target_collection_update(
                id=target_collection['id'],
                name=target_collection['name'],
                description=target_collection['description'],
            )
            db.target_collection_remove_all_compounds(
                id=target_collection['id']
            )
            for created_compound_id in created_compound_ids:
                db.target_collection_add_compound(
                    collection_id=target_collection['id'],
                    compound_id=created_compound_id
                )

        target_collection_ids = get_ids(target_collections)
        await self.notify(
            'target_collection_event', {
                'type': 'update',
                'ids': target_collection_ids
            },
            **{
                **get_client_notification_context(data),
                'room': 'target/collection',
            }
        )
        return {
            'type': 'success',
            'body': None
        }

    async def on_target_collection_delete_request(self, data):
        target_collection_ids = data['value']
        # remove all compounds from the collections
        for target_collection_id in target_collection_ids:
            db.target_collection_remove_all_compounds(
                id=target_collection_id
            )
            db.target_collection_remove_from_all_sample_batches(
                target_collection_id=target_collection_id
            )
        # delete the collection records
        db.target_collection_delete(id=target_collection_ids)

        # N.B - target compounds are NOT deleted here!
        # This is intentional, since dangling compounds are not
        # a problem and can be reused*. Eventual garbage collection
        # could be implemented.
        #
        #                * see on_target_collection_create_request

        await self.notify(
            'target_collection_event', {
                'type': 'delete',
                'ids': target_collection_ids
            },
            **{
                **get_client_notification_context(data),
                'room': 'target/collection',
            }
        )
        return {
            'type': 'success',
            'body': None
        }

    # target compounds
    async def on_target_compound_create_request(self, data):
        raw_compounds = map_to_snake_case(data['value'])
        ionization_mechanisms = db.config_ion_mechanism_read()
        compound_ids = []
        ion_ids = []
        isotope_ids = []

        def norm(name, lower=False):
            if lower:
                name = name.lower()
            return " ".join(name.strip().split())

        def charge_string(raw_ion):
            if raw_ion.charge == -1:
                charge_string = "-"
            elif raw_ion.charge == +1:
                charge_string = "+"
            else:
                charge_string = ""
            return charge_string

        for raw_compound in raw_compounds:
            # check if the compound record is already in the database
            normalized_name = norm(raw_compound['name'], lower=True)
            existing_compounds = list(filter(
                lambda c: norm(c['name'], lower=True) == normalized_name,
                db.target_compound_read(formula=raw_compound['formula'])
            ))
            if len(existing_compounds) == 0:
                # create the compound record if it doesn't exist
                compound = {**raw_compound, 'id': gen_id()}
                db.target_compound_create(**compound)
                compound_ids.append(compound['id'])
            elif len(existing_compounds) == 1:
                # use the existing compound record if it does exist
                compound = existing_compounds[0]
                compound_ids.append(compound['id'])
                continue
            else:
                # the database is inconsistent
                raise RuntimeError('Duplicate target compound in database')

            # generate and create ion records
            for ionization_mechanism in ionization_mechanisms:
                mechanism = ionization_mechanism['mechanism']
                try:
                    # get and save ions
                    raw_ion = Formula(
                            '(' +
                            compound['formula'].rstrip() +
                            mechanism[:-1] +
                            ')' + mechanism[-1]
                        )
                except ValueError:
                    pass
                else:
                    # construct and save ion row
                    ion = {
                        'id': gen_id(),
                        'target_compound_id': compound['id'],
                        'mechanism_id': ionization_mechanism['id'],
                        'formula': raw_ion.formula + charge_string(raw_ion),
                        'polarity': charge_string(raw_ion),
                        'charge': raw_ion.charge,
                    }
                    db.target_ion_create(**ion)
                    ion_ids.append(ion['id'])
                    # construct and save isotope rows
                    raw_isotopes = (
                        get_exact_isotope_mzs(raw_ion.formula)
                        .values()
                    )
                    for raw_isotope in raw_isotopes:
                        [mz, rel_abu] = raw_isotope
                        isotope = {
                            'id': gen_id(),
                            'target_ion_id': ion['id'],
                            'mz': mz,
                            'relative_abundance': rel_abu
                        }
                        db.target_isotope_create(**isotope)
                        isotope_ids.append(isotope['id'])

        created_target_ids = {
            'compound': compound_ids,
            'ion': ion_ids,
            'isotope': isotope_ids
        }
        for level in ['compound', 'ion', 'isotope']:
            await self.notify(
                f"target_{level}_event", {
                    'type': 'create',
                    'ids': created_target_ids[level],
                },
                **{
                    **get_client_notification_context(data),
                    'room': "target/" + level,
                }
            )
        return {
            'type': 'success',
            'body': created_target_ids
        }

    async def on_target_compound_read_request(self, data):
        filters = map_to_snake_case(data['value'])
        target_collection_ids = filters.pop('target_collection_id')
        compounds = []
        for target_collection_id in target_collection_ids:
            target_compound_ids = [
                link['target_compound_id']
                for link in db.target_compound_in_target_collection.read(
                    target_collection_id=target_collection_id
                )
            ]
            # get compounds based on filters
            compounds += [
                {**compound, 'target_collection_id': target_collection_id}
                for compound in db.target_compound_read(
                    id=target_compound_ids,
                    **filters
                )
            ]
        return {
            'type': 'success',
            'body': map_to_camel_case(compounds)
        }

    async def on_target_compound_update_request(self, data):
        return {
            'type': 'failure',
            'body': 'Not implemented'
        }

    async def on_target_compound_delete_request(self, data):
        return {
            'type': 'failure',
            'body': 'Not implemented'
        }

    # ions

    async def on_target_ion_create_request(self, data):
        return {
            'type': 'failure',
            'body': 'Not implemented'
        }

    async def on_target_ion_read_request(self, data):
        filters = map_to_snake_case(data['value'])
        ions = db.target_ion_read(**filters)
        return {
            'type': 'success',
            'body': map_to_camel_case(ions)
        }

    async def on_target_ion_update_request(self, data):
        return {
            'type': 'failure',
            'body': 'Not implemented'
        }

    async def on_target_ion_delete_request(self, data):
        return {
            'type': 'failure',
            'body': 'Not implemented'
        }

    # isotopes

    async def on_target_isotope_create_request(self, data):
        return {
            'type': 'failure',
            'body': 'Not implemented'
        }

    async def on_target_isotope_read_request(self, data):
        filters = map_to_snake_case(data['value'])
        isotopes = db.target_isotope_read(**filters)
        return {
            'type': 'success',
            'body': map_to_camel_case(isotopes)
        }

    async def on_target_isotope_update_request(self, data):
        return {
            'type': 'failure',
            'body': 'Not implemented'
        }

    async def on_target_isotope_delete_request(self, data):
        return {
            'type': 'failure',
            'body': 'Not implemented'
        }

    # MATCHES

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
        mz_tolerance = value['mzTolerance']  # ppm
        iso_abu_tolerance = value['isoAbuTolerance']/100  # %

        # STEP 1 - Get peaks

        # Check if file is cached
        cache_item = cache.get(filename, None)
        if not cache_item:
            # File not in cache, load
            print("Loading file: %s" % filename)
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
                """ % len(filtered_peaks),
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
        target_isotope_df = (
            pd.DataFrame
            .from_dict(value['targetIsotopes'])
            .rename(columns={
                'id': 'targetIsotopeId',
                'ionId': 'targetIonId',
                'compoundId': 'targetCompoundId'
            })
        )

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
        print('Service stopped.')


if __name__ == '__main__':
    run()
