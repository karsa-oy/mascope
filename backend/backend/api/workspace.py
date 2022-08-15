import pandas as pd

from backend.db import init_cursor, gen_id
from backend.server import sio

cur = init_cursor()

@sio.event(namespace='/api')
async def workspace_create(sid, workspaces):
    workspaces = [
        {**workspace, 'id': gen_id()}
        for workspace in workspaces
    ]
    workspace_df = pd.DataFrame.from_records(workspaces)
    cur.execute("""
        INSERT INTO workspace (
            SELECT * FROM workspace_df
        );
    """)
    sio.emit('org_reload', namespace='/api')


@sio.event(namespace='/api')
async def workspace_update(sid, workspaces):
    workspace_df = pd.DataFrame.from_records(workspaces)
    cur.execute(f"""
        UPDATE workspace
        SET {", ".join([
            f"{col}=workspace_df.{col}"
            for col in workspace_df.columns
            if col != 'workspace_id'
        ])}
        WHERE
            workspace.workspace_id == workspace_df.workspace_id;
    """)
    sio.emit('org_reload', namespace='/api')


@sio.event(namespace='/api')
async def workspace_delete(sid, workspace_ids):
    workspace_df = pd.DataFrame.from_dict({
        'workspace_id': workspace_ids
    })
    cur.execute("""
        DELETE FROM target_collection_in_sample_batch
        WHERE sample_batch_id IN (
            SELECT sample_batch_id
            FROM sample_batch
            WHERE workspace_id IN (
                SELECT workspace_id FROM workspace_df
            )
        );
        DELETE FROM sample_item
        WHERE sample_batch_id IN (
            SELECT sample_batch_id
            FROM sample_batch
            WHERE workspace_id IN (
                SELECT workspace_id FROM workspace_df
            )
        );
        DELETE FROM sample_batch
        WHERE workspace_id IN (
            SELECT workspace_id FROM workspace_df
        );
        DELETE FROM workspace
        WHERE workspace_id IN (
            SELECT workspace_id FROM workspace_df
        );
    """)
    sio.emit('org_reload', namespace='/api')
