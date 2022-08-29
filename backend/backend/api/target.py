import pandas as pd

from backend.db.conn import conn
from backend.db.id import gen_id

from backend.lib.molmass import Formula
from backend.lib.chemistry import get_exact_isotope_mzs

from backend.server import sio


# target collections

@sio.event(namespace='/api')
async def target_collection_create(sid, target_collections):
    print(target_collections)
    target_collections = [
        {**target_collection, 'target_collection_id': gen_id()}
        for target_collection in target_collections
        ]
    for target_collection in target_collections:
        # create compounds
        collection_compound_ids = (
            await target_compound_create(
                None,
                target_collection['target_compounds']
                )
            )
        with conn:
            # create collection
            conn.cursor().execute("""
                INSERT INTO target_collection (
                    target_collection_id,
                    name,
                    description
                ) VALUES (?, ?, ?);
                """, [
                target_collection['target_collection_id'],
                target_collection['name'],
                target_collection['description']
                ])
            # add compounds to collection
            for collection_compound_id in collection_compound_ids:
                conn.cursor().execute("""
                    INSERT INTO target_compound_in_target_collection (
                        target_compound_id,
                        target_collection_id
                    ) VALUES (?, ?);
                    """, [
                    collection_compound_id,
                    target_collection['target_collection_id']
                    ])
            # add collection to sample batches
            for sample_batch_id in target_collection.get('sample_batches', []):
                conn.cursor().execute("""
                    INSERT INTO target_collection_in_sample_batch (
                        target_collection_id,
                        sample_batch_id
                    ) VALUES (?, ?);
                    """, [
                    target_collection['target_collection_id'],
                    sample_batch_id
                ])
                await sio.emit('batch_reload', sample_batch_id, namespace='/api')
    await sio.emit('org_reload', namespace='/api')


@sio.event(namespace='/api')
async def target_collection_update(sid, target_collections):
    # TODO:
    # update target collection records
    # target_collection_df = pd.DataFrame.from_records(target_collections)
    # with conn:
    #     cur.execute(f"""
    #         UPDATE target_collection
    #         SET {", ".join([
    #             f"{col}=target_collection_df.{col}"
    #             for col in target_collection_df.columns
    #             if col != 'target_collection_id'
    #         ])}
    #         WHERE
    #             target_collection.target_collection_id
    #                 == target_collection_df.target_collection_id;
    #     """)
    #     for target_collection in target_collections:
    #         target_collection_id = target_collection['target_collection_id']
    #         # change collection compounds if needed
    #         if 'compounds' in target_collection:
    #             # remove all compounds from the collection
    #             cur.execute("""
    #                 DELETE FROM target_compound_in_target_collection
    #                 WHERE target_collection_id == ?
    #             """, [target_collection_id])
    #             # create new compounds
    #             target_compound_ids = await (
    #                 target_compound_create(
    #                     sid, target_collection['compounds']
    #                 )
    #             )
    #             # N.B - instead of updating compounds, we
    #             # simply create new ones and update the collection
    #             # record to link to them.
                
    #             # add the new compounds to the collection
    #             target_compound_df = pd.DataFrame.from_dict({
    #                 'target_compound_id': target_compound_ids
    #             })
    #             cur.execute("""
    #                 INSERT INTO target_compound_in_target_collection (
    #                     target_compound_id, target_collection_id
    #                 ) SELECT (
    #                     target_compound_id, ?
    #                 ) FROM target_compound_df
    #             """, [target_collection_id])
    #         # change collection to sample batch links if necessary
    #         if 'sample_batches' in target_collection:
    #             # identify changes that need to be made
    #             current_sample_batch_ids = cur.execute("""
    #                 SELECT (
    #                     sample_batch_id
    #                 ) FROM target_collection_in_sample_batch
    #                 WHERE target_collection_id == ?
    #             """, [
    #                 target_collection_id
    #             ]).fetchdf()['sample_batch_id'].tolist()
    #             new_sample_batch_ids = target_collection['sample_batches']
    #             batches_to_add = [
    #                     sample_batch_id
    #                     for sample_batch_id in new_sample_batch_ids
    #                     if sample_batch_id not in current_sample_batch_ids
    #             ]
    #             batches_to_add_df = pd.DataFrame.from_dict({
    #                 'sample_batch_id': batches_to_add
    #             })
    #             batches_to_remove = [
    #                     sample_batch_id
    #                     for sample_batch_id in current_sample_batch_ids
    #                     if sample_batch_id not in new_sample_batch_ids
    #             ]
    #             batches_to_remove_df = pd.DataFrame.from_dict({
    #                 'sample_batch_id': batches_to_remove
    #             })
    #             # remove collection from batches if needed
    #             cur.execute("""
    #                 DELETE FROM target_collection_in_sample_batch
    #                 WHERE target_collection_id == ?
    #                 AND sample_batch_id IN (
    #                     SELECT sample_batch_id FROM batches_to_remove_df
    #                 )
    #             """, [target_collection_id])
    #             # add collection to batches if needed
    #             cur.execute("""
    #                 INSERT INTO target_collection_in_sample_batch (
    #                     target_collection_id,
    #                     sample_batch_id
    #                 ) (
    #                     SELECT (?, sample_batch_id)
    #                     FROM batches_to_add_df
    #                 )
    #             """)
    #             # reload affected batches
    #             batches_changed = list(dict.fromkeys(
    #                 batches_to_add + batches_to_remove
    #                 ))
    #             for sample_batch_id in batches_changed:
    #                 await sio.emit('batch_reload', sample_batch_id, namespace='/api')
    # await sio.emit('org_reload', namespace='/api')


@sio.event(namespace='/api')
async def target_collection_delete(sid, target_collection_ids):
    target_collection_id_refs = ','.join('?'*len(target_collection_ids))
    with conn:
        # remove all compounds from the collections
        conn.cursor().execute(f"""
            DELETE FROM target_compound_in_target_collection
            WHERE target_collection_id IN (
                {target_collection_id_refs}
            );
            """,
            target_collection_ids
            )
        # remove the target collections from all sample batches
        conn.cursor().execute(f"""
            DELETE FROM target_collection_in_sample_batch
            WHERE target_collection_id IN (
                {target_collection_id_refs}
            );
            """,
            target_collection_ids
            )
        # finally delete the collection records
        conn.cursor().execute(f"""
            DELETE FROM target_collection
            WHERE target_collection_id IN (
                {target_collection_id_refs}
            );
            """,
            target_collection_ids
            )
    # N.B - target compounds are NOT deleted here!
    # This is intentional, since dangling compounds are not
    # a problem and can be reused*. Eventual garbage collection
    # could be implemented.
    #
    #                * see target_collection_create
    await sio.emit('org_reload', namespace='/api')


# target compounds

@sio.event(namespace='/api')
async def target_compound_create(sid, target_compounds):
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

    # fetch ionization mechanisms
    with conn:
        ionization_mechanisms = pd.read_sql("""
            SELECT * FROM config_mechanism;
            """,
            conn).to_dict('records')

        # initialize list of targets to return
        target_compound_ids = []
        # initalized lists of targets to create
        target_compounds_to_create = []
        target_ions = []
        target_isotopes = []

        for target_compound in target_compounds:
            # check if the compound record is already in the database
            existing_compounds = pd.read_sql("""
                SELECT * FROM target_compound
                WHERE target_compound_formula COLLATE NOCASE==?;
                """,
                conn,
                params=[norm(
                    target_compound['target_compound_formula'],
                    lower=True
                    )]
                ).to_dict('records')
            if len(existing_compounds) == 0:
                # save the new compound for creation if it doesn't exist
                target_compound = {**target_compound, 'target_compound_id': gen_id()}
                target_compound['target_compound_formula'] = norm(
                    target_compound['target_compound_formula']
                    )
                target_compounds_to_create.append(target_compound)
                target_compound_ids.append(target_compound['target_compound_id'])
            elif len(existing_compounds) == 1:
                # use the existing compound record if it does exist
                [target_compound] = existing_compounds
                target_compound_ids.append(target_compound['target_compound_id'])
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
                        target_compound['target_compound_formula'].rstrip() +
                        mechanism[:-1] +
                        ')' + mechanism[-1]
                        )
                except ValueError as e:
                    print("Failed to parse ion formula: %s" %e)
                else:
                    # construct and save ion row
                    ion = {
                        'target_ion_id': gen_id(),
                        'target_compound_id': target_compound['target_compound_id'],
                        'mechanism_id': ionization_mechanism['mechanism_id'],
                        'target_ion_formula': raw_ion.formula + charge_string(raw_ion),
                    }
                    target_ions.append(ion)
                    # construct and save isotope rows
                    raw_isotopes = (
                        get_exact_isotope_mzs(raw_ion.formula)
                        .values()
                    )
                    target_isotopes += [{
                        'target_isotope_id': gen_id(),
                        'target_ion_id': ion['target_ion_id'],
                        'mz': mz,
                        'relative_abundance': rel_abu
                        } for [mz, rel_abu] in raw_isotopes
                    ]
        # create the targets
        target_compound_df = pd.DataFrame.from_records(target_compounds_to_create)
        target_compound_df.to_sql(
            'target_compound',
            conn,
            if_exists='append',
            index=False
            )
        target_ion_df = pd.DataFrame.from_records(target_ions)
        target_ion_df.to_sql(
            'target_ion',
            conn,
            if_exists='append',
            index=False
            )
        target_isotope_df = pd.DataFrame.from_records(target_isotopes)
        target_isotope_df.to_sql(
            'target_isotope',
            conn,
            if_exists='append',
            index=False
            )
    return target_compound_ids
