import json
import os

from .db import DbInstance
from .lib.util import generate_unique_key # TODO: Review key generation method

db_path = 'test.db' # Path to SampleManager database
db = DbInstance(db_path)

projects_path = './Projects'
project_dirs = next( os.walk(projects_path) )[1]

if __name__ == '__main__':
    # workspaces = []
    # batches = []
    # items = []
    # Loop through directories in root, assumed to be named by instrument
    for project_dir in project_dirs:
        # print(project_dir)
        project_dir_path = os.path.join(projects_path, project_dir)
        attrs_path = os.path.join(project_dir_path, '.attrs')
        with open(attrs_path, 'r') as f:
            attrs = json.load(f)
        attrs_dict = {attr['label'].lower(): attr['value'] for attr in attrs}
        workspace = dict(
            id=generate_unique_key(),
            name=attrs_dict.pop('title'),
            description=attrs_dict.pop('description'),
            attributes=json.dumps(attrs_dict)
        )
        # workspaces.append(workspace)
        db.workspace_create(**workspace)
        # Loop through datetime dirs inside
        experiment_dirs = next( os.walk(project_dir_path) )[1]
        for experiment_dir in experiment_dirs:
            # print(experiment_dir)
            experiment_dir_path = os.path.join(project_dir_path, experiment_dir)
            attrs_path = os.path.join(experiment_dir_path, '.attrs')
            with open(attrs_path, 'r') as f:
                attrs = json.load(f)
            attrs_dict = {attr['label'].lower(): attr['value'] for attr in attrs}
            batch = dict(
                id=generate_unique_key(),
                workspaceId=workspace['id'],
                name=attrs_dict.pop('title'),
                description=attrs_dict.pop('description'),
                attributes=json.dumps(attrs_dict)
            )
            # batches.append(batch)
            db.sample_batch_create(**batch)

            item_dirs = next( os.walk(experiment_dir_path) )[1]
            for item_dir in item_dirs:
                # print(item_dir)
                attrs_path = os.path.join(experiment_dir_path, item_dir, '.attrs')
                with open(attrs_path, 'r') as f:
                    attrs = json.load(f)
                attrs_dict = {attr['label'].lower(): attr['value'] for attr in attrs}
                try:
                    description = attrs_dict.pop('description')
                except KeyError:
                    description = ""
                item = dict(
                    id=generate_unique_key(),
                    filename=item_dir,
                    batchId=batch['id'],
                    name=attrs_dict.pop('title'),
                    description=description,
                    attributes=json.dumps(attrs_dict)
                )
                # items.append(item)
                db.sample_item_create(**item)
    # print(workspaces)
    # print(batches)
    # print(items)