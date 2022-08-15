import pandas as pd

from backend.db import init_cursor, gen_id

from backend.lib.molmass import Formula
from backend.lib.chemistry import get_exact_isotope_mzs
from backend.lib.struct import LRUDict

from backend.server import sio

cur = init_cursor()

# File cache
cache = LRUDict(10)


# target collections

@sio.event(namespace='/api')
async def target_collection_create(sid, target_collections):
    target_collections = [
        {**target_collection, 'id': gen_id()}
        for target_collection in target_collections
    ]
    for target_collection in target_collections:
        # create compounds
        created_compound_ids = (
            await target_compound_create(
                target_collection['target_compounds']
            )
        )
        # create collection
        cur.execute("""
            INSERT INTO target_collection (
                id,
                name,
                description
            ) VALUES (?, ?, ?);
        """, [
            target_collection['id'],
            target_collection['name'],
            target_collection['description']
        ])
        # add compounds to collection
        for created_compound_id in created_compound_ids:
            cur.execute("""
                INSERT INTO target_compound_in_target_collection (
                    target_compound_id,
                    target_collection_id
                ) VALUES (?, ?);
            """, [
                created_compound_id,
                target_collection['id']
            ])
        # add collection to sample batches
        for sample_batch_id in target_collection.get('sample_batches', []):
            cur.execute("""
                INSERT INTO target_collection_in_sample_batch (
                    target_collection_id,
                    sample_batch_id
                ) VALUES (?, ?);
            """, [
                target_collection['id'],
                sample_batch_id
            ])
        sio.emit('batch_reload', sample_batch_id, namespace='/api')
    sio.emit('org_reload', namespace='/api')


@sio.event(namespace='/api')
async def target_collection_update(sid, target_collections):
    # update target collection records
    target_collection_df = pd.DataFrame.from_records(target_collections)
    cur.execute(f"""
        UPDATE target_collection
        SET {", ".join([
            f"{col}=target_collection_df.{col}"
            for col in target_collection_df.columns
            if col != 'target_collection_id'
        ])}
        WHERE
            target_collection.target_collection_id
                == target_collection_df.target_collection_id;
    """)
    for target_collection in target_collections:
        target_collection_id = target_collection['target_collection_id']
        # change collection compounds if needed
        if 'compounds' in target_collection:
            # remove all compounds from the collection
            cur.execute("""
                DELETE FROM target_compound_in_target_collection
                WHERE target_collection_id == ?
            """, [target_collection_id])
            # create new compounds
            target_compound_ids = await (
                target_compound_create(
                    sid, target_collection['compounds']
                )
            )
            # N.B - instead of updating compounds, we
            # simply create new ones and update the collection
            # record to link to them.
            
            # add the new compounds to the collection
            target_compound_df = pd.DataFrame.from_dict({
                'target_compound_id': target_compound_ids
            })
            cur.execute("""
                INSERT INTO target_compound_in_target_collection (
                    target_compound_id, target_collection_id
                ) SELECT (
                    target_compound_id, ?
                ) FROM target_compound_df
            """, [target_collection_id])
        # change collection to sample batch links if necessary
        if 'sample_batches' in target_collection:
            # identify changes that need to be made
            current_sample_batch_ids = cur.execute("""
                SELECT (
                    sample_batch_id
                ) FROM target_collection_in_sample_batch
                WHERE target_collection_id == ?
            """, [
                target_collection_id
            ]).fetchdf()['sample_batch_id'].tolist()
            new_sample_batch_ids = target_collection['sample_batches']
            batches_to_add = [
                    sample_batch_id
                    for sample_batch_id in new_sample_batch_ids
                    if sample_batch_id not in current_sample_batch_ids
            ]
            batches_to_add_df = pd.DataFrame.from_dict({
                'sample_batch_id': batches_to_add
            })
            batches_to_remove = [
                    sample_batch_id
                    for sample_batch_id in current_sample_batch_ids
                    if sample_batch_id not in new_sample_batch_ids
            ]
            batches_to_remove_df = pd.DataFrame.from_dict({
                'sample_batch_id': batches_to_remove
            })
            # remove collection from batches if needed
            cur.execute("""
                DELETE FROM target_collection_in_sample_batch
                WHERE target_collection_id == ?
                AND sample_batch_id IN (
                    SELECT sample_batch_id FROM batches_to_remove_df
                )
            """, [target_collection_id])
            # add collection to batches if needed
            cur.execute("""
                INSERT INTO target_collection_in_sample_batch (
                    target_collection_id,
                    sample_batch_id
                ) (
                    SELECT (?, sample_batch_id)
                    FROM batches_to_add_df
                )
            """)
            # reload affected batches
            batches_changed = list(dict.fromkeys(
                batches_to_add + batches_to_remove
            ))
            for sample_batch_id in batches_changed:
                sio.emit('batch_reload', sample_batch_id, namespace='/api')
    sio.emit('org_reload', namespace='/api')


@sio.event(namespace='/api')
async def target_collection_delete(sid, target_collection_ids):
    target_collection_df = pd.DataFrame.from_dict({
        'target_collection_id': target_collection_ids
    })
    # remove all compounds from the collections
    cur.execute("""
        DELETE FROM target_compound_in_target_collection
        WHERE target_collection_id IN (
            SELECT target_collection_id FROM target_collection_df
        );
    """)
    # remove the target collections from all sample batches
    cur.execute("""
        DELETE FROM target_collection_in_sample_batch
        WHERE target_collection_id IN (
            SELECT target_collection_id FROM target_collection_df
        );
    """)
    # finally delete the collection records
    cur.execute("""
        DELETE FROM target_collection
        WHERE target_collection_id IN (
            SELECT target_collection_id FROM target_collection_df
        );
    """)
    # N.B - target compounds are NOT deleted here!
    # This is intentional, since dangling compounds are not
    # a problem and can be reused*. Eventual garbage collection
    # could be implemented.
    #
    #                * see target_collection_create
    sio.emit('org_reload', namespace='/api')


# target compounds

@sio.event(namespace='/api')
async def target_compound_create(sid, target_compounds):
    # fetch ionization mechanisms
    ionization_mechanisms = cur.execute("""
        SELECT * FROM config_mechanism;
    """).fetchdf().to_dict('records')

    # helper functions
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

    # initialize list of targets to return
    target_compound_ids = []

    # initalized lists of targets to create
    target_compounds = []
    target_ions = []
    target_isotopes = []

    for target_compound in target_compounds:
        # check if the compound record is already in the database
        existing_compounds = cur.execute("""
            SELECT * FROM target_compound
            WHERE formula COLLATE NOCASE=?;
        """, [
            norm(target_compound['name'], lower=True)
        ]).fetchdf().to_dict('records')
        if len(existing_compounds) == 0:
            # save the new compound for creation if it doesn't exist
            target_compound = {'id': gen_id(), **target_compound}
            target_compounds.append(target_compound)
            target_compound_ids.append(target_compound['id'])
        elif len(existing_compounds) == 1:
            # use the existing compound record if it does exist
            [target_compound] = existing_compounds
            target_compound_ids.append(target_compound['id'])
            continue  # as ions & isotopes are already there in this case
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
                        target_compound['formula'].rstrip() +
                        mechanism[:-1] +
                        ')' + mechanism[-1]
                    )
            except ValueError:
                pass
            else:
                # construct and save ion row
                ion = {
                    'id': gen_id(),
                    'target_compound_id': target_compound['id'],
                    'mechanism_id': ionization_mechanism['id'],
                    'formula': raw_ion.formula + charge_string(raw_ion),
                }
                target_ions.append(ion)
                # construct and save isotope rows
                raw_isotopes = (
                    get_exact_isotope_mzs(raw_ion.formula)
                    .values()
                )
                target_isotopes += [{
                        'id': gen_id(),
                        'target_ion_id': ion['id'],
                        'mz': mz,
                        'relative_abundance': rel_abu
                    } for [mz, rel_abu] in raw_isotopes
                ]
    # create the targets
    target_compound_df = pd.DataFrame.from_records(target_compounds)
    target_ion_df = pd.DataFrame.from_records(target_ions)
    target_isotope_df = pd.DataFrame.from_records(target_isotopes)
    cur.execute("""
        INSERT INTO target_compound (
            SELECT * FROM target_compound_df
        );
        INSERT INTO target_ion (
            SELECT * FROM target_ion_df
        );
        INSERT INTO target_isotope (
            SELECT * FROM target_isotope_df
        );
    """)
    return target_compound_ids
