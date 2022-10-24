import pandas as pd

from datetime import datetime

from backend.db.conn import conn
from backend.db.id import gen_id
from backend.server import sio


@sio.event(namespace='/')
async def workspace_create(sid, workspaces):
    workspaces = [
        {**workspace, 'workspace_id': gen_id()}
        for workspace in workspaces
    ]
    workspace_df = pd.DataFrame.from_records(workspaces)
    workspace_df['workspace_utc_created'] = [
        datetime.now().isoformat()
        ]*len(workspace_df)
    workspace_df['workspace_utc_modified'] = [
        datetime.now().isoformat()
        ]*len(workspace_df)
    with conn:
        workspace_df.to_sql(
            'workspace',
            conn,
            if_exists='append',
            index=False
            )
    await sio.emit('org_reload', namespace='/')


@sio.event(namespace='/')
async def workspace_update(sid, workspaces):
    workspace_df = pd.DataFrame.from_records(workspaces)
    workspace_df['workspace_utc_modified'] = [
        datetime.now().isoformat()
        ]*len(workspace_df)
    workspace_ids = workspace_df['workspace_id'].tolist()
    workspace_id_refs = ','.join('?'*len(workspace_ids))
    with conn:
        # Delete existing workspace records
        conn.cursor().execute(f"""
            DELETE FROM workspace
            WHERE workspace_id IN ({workspace_id_refs})
            """,
            workspace_ids
            )
        # Create new record with updated data
        workspace_df.to_sql(
            'workspace',
            conn,
            if_exists='append',
            index=False
            )
    await sio.emit('org_reload', namespace='/')


@sio.event(namespace='/')
async def workspace_delete(sid, workspace_ids):
    with conn:
        workspace_id_refs = ','.join('?'*len(workspace_ids))
        conn.cursor().execute(f"""
            DELETE FROM target_collection_in_sample_batch
            WHERE sample_batch_id IN (
                SELECT sample_batch_id
                FROM sample_batch
                WHERE workspace_id IN (
                    {workspace_id_refs}
                )
            )""",
            workspace_ids
        )
        conn.cursor().execute(f"""DELETE FROM sample_item
            WHERE sample_batch_id IN (
                SELECT sample_batch_id
                FROM sample_batch
                WHERE workspace_id IN (
                    {workspace_id_refs}
                )
            )""",
            workspace_ids
        )
        conn.cursor().execute(f"""DELETE FROM sample_batch
            WHERE workspace_id IN (
                {workspace_id_refs}
            )""",
            workspace_ids
        )
        conn.cursor().execute(f"""DELETE FROM workspace
            WHERE workspace_id IN (
                {workspace_id_refs}
            )""",
            workspace_ids
        )
    await sio.emit('org_reload', namespace='/')
