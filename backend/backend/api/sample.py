import pandas as pd
from datetime import timedelta

from backend.db import init_con, gen_id
from backend.lib.util import (
    timestamp_from_filename,
)
from backend.server import sio

con = init_con()
cur = con.cursor()

# === sample batches === #

@sio.event(namespace='/api')
async def sample_batch_create(sid, sample_batches):
    sample_batches = [
        {**sample_batch, 'id': gen_id()}
        for sample_batch in sample_batches
    ]
    sample_batch_df = pd.DataFrame.from_records(sample_batches)
    workspace_ids = cur.execute("""--sql
        SELECT DISTINCT workspace_id
        FROM sample_batch_df
    """).fetchdf()['workspace_id'].tolist()
    if len(workspace_ids) != 1:
        raise ValueError(
            'sample batches created must be in exactly one workspace'
        )
    else:
        cur.execute("""--sql
            INSERT INTO sample_batch (
                SELECT * FROM sample_batch_df
            );
        """)
        [workspace_id] = workspace_ids
        sio.emit('workspace_reload', workspace_id, namespace='/api')


@sio.event(namespace='/api')
async def sample_batch_update(sid, sample_batches):
    sample_batch_df = pd.DataFrame.from_records(sample_batches)
    workspace_ids = cur.execute("""--sql
        SELECT DISTINCT workspace_id
        FROM sample_batch_df
    """).fetchdf()['workspace_id'].tolist()
    if len(workspace_ids) != 1:
        raise ValueError(
            'sample batches updated must be in exactly one workspace'
        )
    else:
        cur.execute(f"""
            UPDATE sample_batch
            SET {", ".join([
                f"{col}=sample_batch_df.{col}"
                for col in sample_batch_df.columns
                if col != 'sample_batch_id'
            ])}
            WHERE
                sample_batch.sample_batch_id
                    == sample_batch_df.sample_batch_id;
        """)
        [workspace_id] = workspace_ids
        sio.emit('workspace_reload', workspace_id, namespace='/api')


@sio.event(namespace='/api')
async def sample_batch_delete(sid, sample_batch_ids):
    sample_batch_df = pd.DataFrame.from_dict({
        'sample_batch_id': sample_batch_ids
    })
    workspace_ids = cur.execute("""--sql
        SELECT DISTINCT workspace_id
        FROM sample_batch
        WHERE sample_batch_id IN (
            SELECT sample_batch_id FROM sample_batch_df
        );
    """).fetchdf()['workspace_id'].tolist()
    if len(workspace_ids) != 1:
        raise ValueError(
            'sample batches deleted must be in exactly one workspace'
        )
    else:
        cur.execute("""--sql
            DELETE FROM target_collection_in_sample_batch
            WHERE sample_batch_id IN (
                SELECT sample_batch_id FROM sample_batch_df
            );
            DELETE FROM sample_item
            WHERE sample_batch_id IN (
                SELECT sample_batch_id FROM sample_batch_df
            );
            DELETE FROM sample_batch
            WHERE sample_batch_id IN (
                SELECT sample_batch_id FROM sample_batch_df
            );
        """)
        [workspace_id] = workspace_ids
        sio.emit('workspace_reload', workspace_id, namespace='/api')


# === sample items === #

@sio.event(namespace='/api')
async def sample_item_create(sid, sample_items):
    sample_items = [
        {**sample_item, 'id': gen_id()}
        for sample_item in sample_items
    ]
    sample_item_df = pd.DataFrame.from_records(sample_items)
    sample_batch_ids = cur.execute("""--sql
        SELECT DISTINCT sample_batch_id
        FROM sample_item_df
    """).fetchdf()['sample_batch_id'].tolist()
    if len(sample_batch_ids) != 1:
        raise ValueError(
            'sample items created must be in exactly one sample batch'
        )
    else:
        cur.execute("""--sql
            INSERT INTO sample_item (
                SELECT * FROM sample_item_df
            );
        """)
        [sample_batch_id] = sample_batch_ids
        sio.emit('batch_reload', sample_batch_id, namespace='/api')


@sio.event(namespace='/api')
async def sample_item_update(sid, sample_items):
    sample_item_df = pd.DataFrame.from_records(sample_items)
    sample_batch_ids = cur.execute("""--sql
        SELECT DISTINCT sample_batch_id
        FROM sample_item_df
    """).fetchdf()['sample_batch_id'].tolist()
    if len(sample_batch_ids) != 1:
        raise ValueError(
            'sample items updated must be in exactly one workspace'
        )
    else:
        cur.execute(f"""
            UPDATE sample_item
            SET {", ".join([
                f"{col}=sample_item_df.{col}"
                for col in sample_item_df.columns
                if col != 'sample_item_id'
            ])}
            WHERE
                sample_item.sample_item_id
                    == sample_item_df.sample_item_id;
        """)
        [sample_batch_id] = sample_batch_ids
        sio.emit('batch_reload', sample_batch_id, namespace='/api')


@sio.event(namespace='/api')
async def sample_item_delete(sid, sample_item_ids):
    sample_item_df = pd.DataFrame.from_dict({
        'sample_item_id': sample_item_ids
    })
    sample_batch_ids = cur.execute("""--sql
        SELECT DISTINCT sample_batch_id
        FROM sample_item
        WHERE sample_item_id IN (
            SELECT sample_item_id FROM sample_item_df
        );
    """).fetchdf()['sample_batch_id'].tolist()
    if len(sample_batch_ids) != 1:
        raise ValueError(
            'sample items deleted must be in exactly one workspace'
        )
    else:
        cur.execute("""--sql
            DELETE FROM target_collection_in_sample_item
            WHERE sample_item_id IN (
                SELECT sample_item_id FROM sample_item_df
            );
            DELETE FROM sample_item
            WHERE sample_item_id IN (
                SELECT sample_item_id FROM sample_item_df
            );
            DELETE FROM sample_item
            WHERE sample_item_id IN (
                SELECT sample_item_id FROM sample_item_df
            );
        """)
        [sample_batch_id] = sample_batch_ids
        sio.emit('batch_reload', sample_batch_id, namespace='/api')


# === sample files === #

@sio.event(namespace='/api')
async def sample_file_create(sid, sample_files):
    sample_files = [
        {**sample_file, 'id': gen_id()}
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
    if data['data_type'] != 'signal':
        raise ValueError(
            f"Expected data_type: signal - got {data['data_type']}"
        )
    filename = data['filename']
    full_length = data['length']
    committed_length = data['committed_length']
    if committed_length >= full_length:
        instrument = filename.split('_')[0]
        date = timestamp_from_filename(filename)
        title = data.get('title', "")
        utc_offset = timedelta(seconds=int(data['utc_offset']))
        sample_file_create([{
            "id": filename,
            "filename": filename,
            "instrument": instrument,
            "title": title,
            "datetime": date.isoformat(),
            "datetime_utc": (date - utc_offset).isoformat(),
            "length": committed_length,
            "range": data['range']
        }])
