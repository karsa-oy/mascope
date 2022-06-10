# -*- coding: utf-8 -*-
"""
Created on Mon Apr  4 12:05:10 2022

@author: Karsa

Unzip test dataset and build DbInstance
"""


import os
import json
import shutil

from karsalib.util import parse_datetime_from_item_filename, generate_unique_key
from karsalib.db.instance import DbInstance


delete_zips = False

path = r'/data/instrument' # Path to mascope_test_data directory

db_path = os.path.join(path, 'mascope.db')
#db_path = ':memory'

if __name__ == '__main__':
    db = DbInstance()
    
    workspaces = dict()
    batches = dict()
    
    instrument_dirs = next( os.walk(os.path.join(path)) )[1]
    for i, instrument_dir in enumerate(instrument_dirs):
        dt_dirs = next( os.walk(os.path.join(path, instrument_dir)) )[1]
        for j, dt_dir in enumerate(dt_dirs):
            dt_dir_path = os.path.join(path, instrument_dir, dt_dir)
            sample_zips = next( os.walk(dt_dir_path) )[2]
            for k, sample_zip in enumerate(sample_zips):
                print("instrument_dir {:d}/{:d}; dt_dir {:d}/{:d}; sample_zip {:d}/{:d}"
                      .format(i+1, len(instrument_dirs),
                              j+1, len(dt_dirs),
                              k+1, len(sample_zips)
                              )
                      )
                sample_zip_path = os.path.join(path, instrument_dir, dt_dir, sample_zip)
                sample_dir = sample_zip_path.strip('.zip')
                props_path = os.path.join(dt_dir_path, sample_dir, '.props')
                attrs_path = os.path.join(dt_dir_path, sample_dir, '.attrs')
                # Extract zip
                shutil.unpack_archive(sample_zip_path, sample_dir, 'zip')
                # Delete zip
                if delete_zips:
                    os.remove(sample_zip_path)
                # Read sample properties and attributes, and parse together
                with open(props_path, 'r') as f:
                    props = json.load(f)
                try:
                    with open(attrs_path, 'r') as f:
                        attrs = json.load(f)
                    attrs_dict = {attr['label'].lower(): attr['value'] for attr in attrs}
                except:
                    attrs_dict = {'title': "", 'description': ""}
                try:
                    description = attrs_dict.pop('description')
                except KeyError:
                    description = ""
                    
                try:
                    project = attrs_dict.pop('project')
                    experiment = attrs_dict.pop('experiment')                  
                except KeyError:
                    project = None
                    experiment = None
                    
                sample = dict(
                    id = props['filename'],
                    filename = props['filename'],
                    instrument = props['filename'].split('_')[0],
                    datetime = parse_datetime_from_item_filename(props['filename']).isoformat(),
                    length=props['length'],
                    range=json.dumps(props['range']),
                    title=attrs_dict.pop('title') or props['filename'],
                    description=description,
                    attributes=json.dumps(attrs_dict)
                )
                # Make sample file database record
                db.sample_file_insert(**sample)  
                if project is not None and experiment is not None:
                    if project not in workspaces:
                        workspace_id = generate_unique_key()
                        db.workspace_create(id=workspace_id, name=project)
                        workspaces.update({project: workspace_id})
                    if experiment not in batches:
                        batch_id = generate_unique_key()
                        db.sample_batch_create(id=batch_id, name=experiment, workspaceId=workspaces.get(project))
                        batches.update({experiment: batch_id})
                    sample_item = dict(
                        id = generate_unique_key(),
                        batchId = batches.get(experiment),
                        filename = sample['filename'],
                        title = sample['title'],
                        description = sample['description'],
                        attributes = sample['attributes']
                    )
                    db.sample_item_insert(**sample_item)
    db.con.close()