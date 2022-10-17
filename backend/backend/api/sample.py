import json
import pandas as pd

from backend.api.match import match_batch_compute, match_item_compute
from backend.api.signal import signal_mz_calibration_update
from backend.db.conn import conn
from backend.db.id import gen_id
from backend.server import sio

# === sample batches === #

@sio.event(namespace='/')
async def sample_batch_create(sid, sample_batches):
    sample_batches = [
        {**sample_batch, 'sample_batch_id': gen_id()}
        for sample_batch in sample_batches
    ]
    sample_batch_df = pd.DataFrame.from_records(sample_batches)
    with conn:
        workspace_ids = pd.unique(sample_batch_df['workspace_id']).tolist()
        if len(workspace_ids) != 1:
            raise ValueError(
                'sample batches created must be in exactly one workspace'
            )
        sample_batch_df = sample_batch_df.assign(
            build_params=sample_batch_df[['build_params']].applymap(
                lambda x: json.dumps(x)
            ),
            filter_params=sample_batch_df[['filter_params']].applymap(
                lambda x: json.dumps(x)
            )
        )
        sample_batch_df.drop(columns=['target_collection_id']).to_sql(
            'sample_batch',
            conn,
            if_exists='append',
            index=False
            )
        target_collection_in_sample_batch_df = sample_batch_df[
            ['target_collection_id', 'sample_batch_id']
            ].explode('target_collection_id', ignore_index=True).dropna()
        target_collection_in_sample_batch_df.to_sql(
            'target_collection_in_sample_batch',
            conn,
            if_exists='append',
            index=False
            )
        [workspace_id] = workspace_ids
        await sio.emit('workspace_reload', room=workspace_id, namespace='/')


@sio.event(namespace='/')
async def sample_batch_update(sid, sample_batches):
    for sample_batch in sample_batches:
        sample_batch_df = pd.DataFrame.from_records([sample_batch])
        print(sample_batch_df.to_string())
        workspace_ids = pd.unique(sample_batch_df['workspace_id']).tolist()
        if len(workspace_ids) != 1:
            raise ValueError(
                'sample batches updated must be in exactly one workspace'
            )
        [sample_batch_id] = sample_batch_df['sample_batch_id'].tolist()
        with conn:
            def need_for_rematch():
                # Get difference in target collections
                target_collection_ids_old = pd.read_sql(f"""--sql
                    SELECT target_collection_id
                    FROM target_collection_in_sample_batch
                    WHERE sample_batch_id == ?
                    """,
                    conn,
                    params=[sample_batch_id]
                    )['target_collection_id'].tolist()
                target_collection_ids_new = sample_batch_df['target_collection_id'].tolist()[0]
                target_collections_to_match = [
                    id for id in target_collection_ids_new 
                    if id not in target_collection_ids_old
                    ]
                ion_mechanism_ids_new = sample_batch_df['build_params'].tolist()[0]['ion_mechanisms']
                if len(target_collections_to_match) > 0:
                    ion_mechanisms_to_match = ion_mechanism_ids_new
                else:
                    # Get difference in ionization mechanisms
                    ion_mechanism_ids_old = json.loads(
                        pd.read_sql(f"""--sql
                            SELECT build_params
                            FROM sample_batch
                            WHERE sample_batch_id == ?
                            """,
                            conn,
                            params=[sample_batch_id]
                            )['build_params'].tolist()[0]
                        )['ion_mechanisms']
                    ion_mechanisms_to_match = [
                        id for id in ion_mechanism_ids_new 
                        if id not in ion_mechanism_ids_old
                        ]
                print("target_collections_to_match: %s" %target_collections_to_match)
                print("ion_mechanisms_to_match: %s" %ion_mechanisms_to_match)
                # Return true if either new target collections or new ionization mechanisms
                return len(target_collections_to_match) or len(ion_mechanisms_to_match)
            rematch = need_for_rematch()
            # Delete existing sample batch records
            conn.cursor().execute(f"""
                DELETE FROM sample_batch
                WHERE sample_batch_id == ?
                """,
                [sample_batch_id]
                )
            conn.cursor().execute(f"""
                DELETE FROM target_collection_in_sample_batch
                WHERE sample_batch_id == ?
                """,
                [sample_batch_id]
                )
            # Create new records with updated data
            sample_batch_df = sample_batch_df.assign(
                build_params=sample_batch_df[['build_params']].applymap(
                    lambda x: json.dumps(x)
                ),
                filter_params=sample_batch_df[['filter_params']].applymap(
                    lambda x: json.dumps(x)
                )
            )
            sample_batch_df.drop(columns=['target_collection_id']).to_sql(
                'sample_batch',
                conn,
                if_exists='append',
                index=False
                )
            target_collection_in_sample_batch_df = sample_batch_df[
                ['target_collection_id', 'sample_batch_id']
                ].explode('target_collection_id', ignore_index=True).dropna()
            target_collection_in_sample_batch_df.to_sql(
                'target_collection_in_sample_batch',
                conn,
                if_exists='append',
                index=False
                )
        if rematch:
            await match_batch_compute(sid, sample_batch_id)
        else:
            [workspace_id] = workspace_ids
            await sio.emit(
                'sample_batch_updated',
                room=workspace_id,
                namespace='/'
                )


@sio.event(namespace='/')
async def sample_batch_delete(sid, sample_batch_ids):
    with conn:
        sample_batch_id_refs = ','.join('?'*len(sample_batch_ids))
        workspace_ids = pd.read_sql(f"""--sql
            SELECT DISTINCT workspace_id
            FROM sample_batch
            WHERE sample_batch_id IN (
                {sample_batch_id_refs}
            )
            """,
            conn,
            params=sample_batch_ids
            )['workspace_id'].tolist()
        if len(workspace_ids) != 1:
            raise ValueError(
                'sample batches deleted must be in exactly one workspace'
            )
        else:
            conn.cursor().execute(f"""--sql
                DELETE FROM target_collection_in_sample_batch
                WHERE sample_batch_id IN (
                    {sample_batch_id_refs}
                )
                """,
                sample_batch_ids
            )
            conn.cursor().execute(f"""DELETE FROM sample_item
                WHERE sample_batch_id IN (
                    {sample_batch_id_refs}
                )
                """,
                sample_batch_ids
            )
            conn.cursor().execute(f"""DELETE FROM sample_batch
                WHERE sample_batch_id IN (
                    {sample_batch_id_refs}
                )
                """,
                sample_batch_ids
            )
            [workspace_id] = workspace_ids
            await sio.emit('workspace_reload', room=workspace_id, namespace='/')


# === sample items === #

@sio.event(namespace='/')
async def sample_item_create(sid, sample_items):
    sample_items = [
        {**sample_item, 'sample_item_id': gen_id()}
        for sample_item in sample_items
    ]
    sample_item_df = pd.DataFrame.from_records(sample_items)
    with conn:
        sample_batch_ids = pd.unique(sample_item_df['sample_batch_id']).tolist()
        if len(sample_batch_ids) != 1:
            raise ValueError(
                'sample items created must be in exactly one sample batch'
            )
        [sample_batch_id] = sample_batch_ids
        sample_item_df = sample_item_df.assign(
            sample_item_attributes=sample_item_df[['sample_item_attributes']].applymap(
                lambda x: json.dumps(x)
                ),
            )
        sample_item_df.to_sql(
            'sample_item',
            conn,
            if_exists='append',
            index=False
            )
    sample_item_ids = sample_item_df['sample_item_id'].tolist()
    for sample_item_id in sample_item_ids:
        # await match_item_compute(sid, sample_item_id)
        await sio.emit(
            'sample_item_created',
            sample_item_id,
            room=sid,
            namespace='/'
            )
    await sio.emit(
        'sample_batch_updated',
        room=sample_batch_id,
        namespace='/'
        )


@sio.event(namespace='/')
async def sample_item_update(sid, sample_items):
    sample_item_df = pd.DataFrame.from_records(sample_items)
    sample_batch_ids = pd.unique(sample_item_df['sample_batch_id']).tolist()
    if len(sample_batch_ids) != 1:
        raise ValueError(
            'sample items updated must be in exactly one workspace'
        )
    else:
        sample_item_ids = sample_item_df['sample_item_id'].tolist()
        sample_item_id_refs = ','.join('?'*len(sample_item_ids))
        sample_item_df = sample_item_df.assign(
            sample_item_attributes=sample_item_df[['sample_item_attributes']].applymap(
                lambda x: json.dumps(x)
                ),
            )
        with conn:
            # Delete existing sample item records
            conn.cursor().execute(f"""
                DELETE FROM sample_item
                WHERE sample_item_id IN ({sample_item_id_refs})
                """,
                sample_item_ids
                )
            # Create new records with updated data
            sample_item_df[[
                'sample_item_id',
                'sample_batch_id',
                'filename',
                'sample_item_attributes',
                'sample_item_name',
                'sample_item_type'
                ]].to_sql(
                    'sample_item',
                    conn,
                    if_exists='append',
                    index=False
                    )
        [sample_batch_id] = sample_batch_ids
        await sio.emit(
            'sample_batch_updated',
            room=sample_batch_id,
            namespace='/'
            )

@sio.event(namespace='/')
async def sample_item_delete(sid, sample_item_ids):
    sample_item_id_refs = ','.join('?'*len(sample_item_ids))
    with conn:
        sample_batch_ids = pd.read_sql(f"""--sql
            SELECT DISTINCT sample_batch_id
            FROM sample_item
            WHERE sample_item_id IN (
                {sample_item_id_refs}
            )
            """,
            conn,
            params=sample_item_ids
            )['sample_batch_id'].tolist()
        sample_batch_id_refs = ','.join('?'*len(sample_batch_ids))
        workspace_ids = pd.read_sql(f"""--sql
            SELECT DISTINCT workspace_id
            FROM sample_batch
            WHERE sample_batch_id IN (
                {sample_batch_id_refs}
            )
            """,
            conn,
            params=sample_batch_ids
            )['workspace_id'].tolist()
        if len(workspace_ids) != 1:
            raise ValueError(
                'sample items deleted must be in exactly one workspace'
            )
        else:
            # Delete existing sample item records
            conn.cursor().execute(f"""
                DELETE FROM sample_item
                WHERE sample_item_id IN ({sample_item_id_refs})
                """,
                sample_item_ids
                )
            [sample_batch_id] = sample_batch_ids
            await sio.emit(
                'sample_batch_updated',
                room=sample_batch_id,
                namespace='/'
                )


# === sample files === #

@sio.event(namespace='/')
async def sample_file_create(sid, sample_files):
    sample_files = [
        {**sample_file, 'sample_file_id': gen_id()}
        for sample_file in sample_files
        ]
    sample_file_df = pd.DataFrame.from_records(sample_files)

    instruments = pd.unique(sample_file_df['instrument']).tolist()
    if len(instruments) != 1:
        raise ValueError(
            'sample files created must be from exactly one instrument'
        )

    sample_file_df = sample_file_df.assign(
        sample_file_attributes=sample_file_df[['sample_file_attributes']].applymap(
            lambda x: json.dumps(x)
            ) if 'sample_file_attributes' in sample_file_df else [None]*len(sample_files),
        mz_calibration=sample_file_df[['mz_calibration']].applymap(
            lambda x: json.dumps(x) if x is not None else x
            ) if 'mz_calibration' in sample_file_df else [None]*len(sample_files),
        range=sample_file_df[['range']].applymap(
            lambda x: json.dumps(x)
            ) if 'range' in sample_file_df else [None]*len(sample_files),
        )
    with conn:
        sample_file_df.to_sql(
            'sample_file',
            conn,
            if_exists='append',
            index=False
            )
    for instrument in pd.unique(sample_file_df['instrument']).tolist():
        await sio.emit('sample_file_created', room=instrument, namespace='/')


@sio.event(namespace='/')
async def sample_file_update(sid, sample_files):
    sample_file_df = pd.DataFrame.from_records(sample_files)
    sample_file_df = sample_file_df.assign(
        sample_file_attributes=sample_file_df[['sample_file_attributes']].applymap(
            lambda x: json.dumps(x)
            ),
        mz_calibration=sample_file_df[['mz_calibration']].applymap(
            lambda x: json.dumps(x) if x is not None else x
            ),
        range=sample_file_df[['range']].applymap(
            lambda x: json.dumps(x)
            ),
        )
    with conn:
        sample_file_ids = sample_file_df['sample_file_id'].tolist()
        sample_file_id_refs = ','.join('?'*len(sample_file_ids))
        # Delete existing sample item records
        conn.cursor().execute(f"""
            DELETE FROM sample_file
            WHERE sample_file_id IN ({sample_file_id_refs})
            """,
            sample_file_ids
            )
        # Create new records with updated data
        sample_file_df.to_sql(
            'sample_file',
            conn,
            if_exists='append',
            index=False
            )
    for instrument in pd.unique(sample_file_df['instrument']).tolist():
        await sio.emit('sample_file_updated', room=instrument, namespace='/')