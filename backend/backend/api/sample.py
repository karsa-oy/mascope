import json
import pandas as pd
from datetime import timedelta

from backend.db.conn import conn
from backend.db.id import gen_id
from backend.lib.util import (
    timestamp_from_filename,
)
from backend.server import sio

# === sample batches === #

@sio.event(namespace='/api')
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
        else:
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
            await sio.emit('workspace_reload', workspace_id, namespace='/api')


@sio.event(namespace='/api')
async def sample_batch_update(sid, sample_batches):
    sample_batch_df = pd.DataFrame.from_records(sample_batches)
    print(sample_batch_df.to_string())
    workspace_ids = pd.unique(sample_batch_df['workspace_id']).tolist()
    if len(workspace_ids) != 1:
        raise ValueError(
            'sample batches updated must be in exactly one workspace'
        )
    else:
        sample_batch_ids = sample_batch_df['sample_batch_id'].tolist()
        sample_batch_id_refs = ','.join('?'*len(sample_batch_ids))
        sample_batch_df = sample_batch_df.assign(
            build_params=sample_batch_df[['build_params']].applymap(
                lambda x: json.dumps(x)
            ),
            filter_params=sample_batch_df[['filter_params']].applymap(
                lambda x: json.dumps(x)
            )
        )
        with conn:
            # Delete existing sample batch records
            conn.cursor().execute(f"""
                DELETE FROM sample_batch
                WHERE sample_batch_id IN ({sample_batch_id_refs})
                """,
                sample_batch_ids
                )
            conn.cursor().execute(f"""
                DELETE FROM target_collection_in_sample_batch
                WHERE sample_batch_id IN ({sample_batch_id_refs})
                """,
                sample_batch_ids
                )
            # Create new records with updated data
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
        await sio.emit('workspace_reload', workspace_id, namespace='/api')


@sio.event(namespace='/api')
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
            await sio.emit('workspace_reload', workspace_id, namespace='/api')


# === sample items === #

@sio.event(namespace='/api')
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
        else:
            sample_item_df = sample_item_df.assign(
                attributes=sample_item_df[['attributes']].applymap(
                    lambda x: json.dumps(x)
                    ),
                )
            sample_item_df.to_sql(
                'sample_item',
                conn,
                if_exists='append',
                index=False
                )
            [sample_batch_id] = sample_batch_ids
            await sio.emit('batch_reload', sample_batch_id, namespace='/api')


@sio.event(namespace='/api')
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
            attributes=sample_item_df[['attributes']].applymap(
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
                'title',
                'description',
                'attributes'
                ]].to_sql(
                    'sample_item',
                    conn,
                    if_exists='append',
                    index=False
                    )
        [sample_batch_id] = sample_batch_ids
        await sio.emit('batch_reload', sample_batch_id, namespace='/api')


@sio.event(namespace='/api')
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
            await sio.emit('batch_reload', sample_batch_id, namespace='/api')


# === sample files === #

@sio.event(namespace='/api')
async def sample_file_create(sid, sample_files):
    sample_files = [
        {'id': gen_id(), **sample_file}
        for sample_file in sample_files
    ]
    sample_file_df = pd.DataFrame.from_records(sample_files)
    cur.execute("""--sql
        INSERT INTO sample_file (
            SELECT * FROM sample_file_df
        );
    """)


@sio.event(namespace='/api')
async def sample_file_update(sid, sample_files):
    sample_file_df = pd.DataFrame.from_records(sample_files)
    cur.execute(f"""
        UPDATE sample_file
        SET {", ".join([
            f"{col}=sample_file_df.{col}"
            for col in sample_file_df.columns
            if col != 'sample_file_id'
        ])}
        WHERE
            sample_file.sample_file_id
                == sample_file_df.sample_file_id;
    """)


@sio.event(namespace='/api')
async def dataset_updated(sid, data):
    filename = data['filename']
    full_length = data['length']
    committed_length = data['committed_length']
    if committed_length >= full_length:
        instrument = filename.split('_')[0]
        date = timestamp_from_filename(filename)
        title = data.get('title', "")
        description = data.get('description', "")
        utc_offset = timedelta(seconds=int(data['utc_offset']))
        await sample_file_create(
            None,
            [{
                "filename": filename,
                "title": title,
                "description": description,
                "instrument": instrument,
                "datetime": date.isoformat(),
                "datetime_utc": (date - utc_offset).isoformat(),
                "length": committed_length,
                "range": data['range'],
                "mz_calibration": {},
                "attributes": {},
            }]
        )
