import pandas as pd

from backend.db import init_con, gen_id
from backend.server import sio

con = init_con()
cur = con.cursor()


@sio.event(namespace='/api')
async def attribute_template_create(sid, attribute_templates):
    attribute_templates = [
        {**attribute_template, 'id': gen_id()}
        for attribute_template in attribute_templates
    ]
    attribute_template_df = pd.DataFrame.from_records(attribute_templates)
    cur.execute("""
        INSERT INTO attribute_template (
            SELECT * FROM attribute_template_df
        );
    """)
    sio.emit('org_reload', namespace='/api')


@sio.event(namespace='/api')
async def attribute_template_update(sid, attribute_templates):
    attribute_template_df = pd.DataFrame.from_records(attribute_templates)
    cur.execute(f"""
        UPDATE attribute_template
        SET {", ".join([
            f"{col}=attribute_template_df.{col}"
            for col in attribute_template_df.columns
            if col != 'attribute_template_id'
        ])}
        WHERE
            attribute_template.attribute_template_id
                == attribute_template_df.attribute_template_id;
    """)
    sio.emit('org_reload', namespace='/api')


@sio.event(namespace='/api')
async def attribute_template_delete(sid, attribute_template_ids):
    attribute_template_df = pd.DataFrame.from_dict({
        'attribute_template_id': attribute_template_ids
    })
    cur.execute("""
        DELETE FROM attribute_template
        WHERE attribute_template_id IN (
            SELECT attribute_template_id FROM attribute_template_df
        );
    """)
    sio.emit('org_reload', namespace='/api')
