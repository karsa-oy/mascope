import json
import pandas as pd

from backend.db.conn import conn
from backend.db.id import gen_id
from backend.server import sio



@sio.event(namespace='/')
async def attribute_template_create(sid, attribute_templates):
    attribute_templates = [
        {**attribute_template, 'attribute_template_id': gen_id()}
        for attribute_template in attribute_templates
    ]
    attribute_template_df = pd.DataFrame.from_records(attribute_templates)
    attribute_template_df = attribute_template_df.assign(
            template=attribute_template_df[['template']].applymap(
                lambda x: json.dumps(x)
                ),
            )
    with conn:
        attribute_template_df.to_sql(
            'attribute_template',
            conn,
            if_exists='append',
            index=False
            )
    await sio.emit('org_reload', namespace='/')


@sio.event(namespace='/')
async def attribute_template_update(sid, attribute_templates):
    attribute_template_df = pd.DataFrame.from_records(attribute_templates)
    with conn:
        # Delete existing template records
        attribute_template_ids = attribute_template_df['attribute_template_id'].tolist()
        attribute_template_id_refs = ','.join('?'*len(attribute_template_ids))
        conn.cursor().execute(f"""
            DELETE FROM attribute_template
            WHERE attribute_template_id IN (
                {attribute_template_id_refs}
            )
            """,
            attribute_template_ids
        )
        # Write updated records
        attribute_template_df.to_sql(
            'attribute_template',
            conn,
            if_exists='append',
            index=False
            )
    await sio.emit('org_reload', namespace='/')


@sio.event(namespace='/')
async def attribute_template_delete(sid, attribute_template_ids):
    with conn:
        attribute_template_id_refs = ','.join('?'*len(attribute_template_ids))
        conn.cursor().execute(f"""
            DELETE FROM attribute_template
            WHERE attribute_template_id IN (
                {attribute_template_id_refs}
            )
            """,
            attribute_template_ids
            )
    await sio.emit('org_reload', namespace='/')
