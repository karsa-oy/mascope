import os
import sqlite3
from ..lib.logging import (
    NO_LOGGING_DEFAULT,
    parent_func_name,
)

from .schema import (
    # workspaces
    WorkspaceTable,
    # samples
    SampleBatchTable,
    SampleItemTable,
    SampleFileTable,
    # targets
    TargetCollectionTable,
    TargetCompoundTable,
    TargetIonTable,
    TargetIsotopeTable,
    TargetCompoundInTargetCollectionTable,
    TargetCollectionInSampleBatchTable,
    # configs
    ConfigIonMechanismTable,
    # templates
    AttributeTemplateTable
)


class DbInstance:
    def log(self, *arg):
        if not NO_LOGGING_DEFAULT:
            print(f"[{self.__class__.__name__}.{parent_func_name()}]", *arg)

    def __init__(self, db_path=None):
        self.con = None
        if not db_path:
            data_path = os.environ.get('MASCOPE_DATADIR', '.')
            db_path = os.path.join(data_path, 'mascope.db')
        self._connect(db_path)

    def __del__(self):
        if self.con:
            self.con.close()

    def _connect(self, db_path):
        self.log(db_path)
        try:
            self.con = sqlite3.connect(db_path)
            self.cur = self.con.cursor()
        except Exception as e:
            self.log(f'{e.__class__.__name__}({str(e)})')
            raise
        # configs
        self.config_ion_mechanisms = ConfigIonMechanismTable(self)
        # workspaces
        self.workspaces = WorkspaceTable(self)
        # samples
        self.sample_batches = SampleBatchTable(self)
        self.sample_items = SampleItemTable(self)
        self.sample_files = SampleFileTable(self)
        # targets
        self.target_collections = TargetCollectionTable(self)
        self.target_compounds = TargetCompoundTable(self)
        self.target_ions = TargetIonTable(self)
        self.target_isotopes = TargetIsotopeTable(self)
        self.target_compound_in_target_collection = \
            TargetCompoundInTargetCollectionTable(self)
        self.target_collection_in_sample_batch = \
            TargetCollectionInSampleBatchTable(self)
        # templates
        self.attribute_templates = AttributeTemplateTable(self)

    # WORKSPACES

    def workspace_create(self, **row):
        self.workspaces.create(**row)

    def workspace_read(self, **filters):
        return self.workspaces.read(**filters)

    def workspace_update(self, **row):
        self.workspaces.update(**row)

    def workspace_delete(self, **filters):
        self.workspaces.delete(**filters)

    # SAMPLES

    # sample batches
    def sample_batch_create(self, **row):
        self.sample_batches.create(**row)

    def sample_batch_read(self, **filters):
        return self.sample_batches.read(**filters)

    def sample_batch_update(self, **row):
        self.sample_batches.update(**row)

    def sample_batch_delete(self, **filters):
        self.sample_batches.delete(**filters)

    # sample items
    def sample_item_create(self, **row):
        self.sample_items.create(**row)

    def sample_item_read(self, **filters):
        return self.sample_items.get_joined(
            'sample_files', 'filename', 'id',
            **filters
        )

    def sample_item_update(self, **row):
        # Update sample metadata and not sample file
        self.sample_items.update(**row)

    def sample_item_delete(self, **filters):
        self.sample_items.delete(**filters)

    def sample_item_get(self, **kwargs):
        return self.sample_items.read(**kwargs)

    def sample_item_insert(self, **kwargs):
        # creates or updates sample item
        self.sample_items.insert(**kwargs)

    def sample_item_get_schema(self):
        return [
            name for name, *_
            in self.sample_items.schema
        ]

    # sample files
    def sample_file_get(self, **kwargs):
        return self.sample_files.read(**kwargs)

    def sample_file_get_range(self, *args, **kwargs):
        return self.sample_files.between(*args, **kwargs)

    def sample_file_insert(self, **kwargs):
        self.sample_files.insert(**kwargs)

    def sample_file_get_schema(self):
        res = [name for name, *_ in self.sample_files.schema]
        return res

    # TARGETS

    # target collections
    def target_collection_create(self, **row):
        self.target_collections.create(**row)

    def target_collection_read(self, **filters):
        return self.target_collections.read(**filters)

    def target_collection_update(self, **row):
        self.target_collections.update(**row)

    def target_collection_delete(self, **filters):
        self.target_collections.delete(**filters)

    # target collection / compound membership
    def target_collection_add_compound(self, compound_id, collection_id):
        self.target_compound_in_target_collection.create(
            target_compound_id=compound_id,
            target_collection_id=collection_id
        )

    def target_collection_remove_compound(self, compound_id, collection_id):
        self.target_compound_in_target_collection.delete(
            target_compound_id=compound_id,
            target_collection_id=collection_id
        )

    def target_collection_remove_all_compounds(self, id):
        self.target_compound_in_target_collection.delete(
            target_collection_id=id
        )

    def target_collection_list_compounds(self, id):
        self.target_compound_in_target_collection.read(
            target_collection_id=id
        )

    # target collection / sample batch link
    def target_collection_add_to_sample_batch(
            self,
            target_collection_id,
            sample_batch_id,
            ):
        self.target_collection_in_sample_batch.create(
            target_collection_id=target_collection_id,
            sample_batch_id=sample_batch_id
        )

    def target_collection_remove_from_sample_batch(
            self,
            target_collection_id,
            sample_batch_id,
            ):
        self.target_collection_in_sample_batch.delete(
            target_collection_id=target_collection_id,
            sample_batch_id=sample_batch_id
        )

    def target_collection_remove_from_all_sample_batches(
            self,
            target_collection_id
            ):
        self.target_collection_in_sample_batch.delete(
            target_collection_id=target_collection_id
        )

    # target compounds
    def target_compound_create(self, **row):
        self.target_compounds.create(**row)

    def target_compound_read(self, **filters):
        return self.target_compounds.read(**filters)

    def target_compound_update(self, **row):
        self.target_compounds.update(**row)

    def target_compound_delete(self, **filters):
        self.target_compounds.delete(**filters)

    def target_compound_list_collections(self, id):
        self.target_compound_in_collection.read(
            target_compound_id=id
        )

    # target ions
    def target_ion_create(self, **row):
        self.target_ions.create(**row)

    def target_ion_read(self, **filters):
        return self.target_ions.get_joined(
            'config_ion_mechanisms', 'mechanism_id', 'id',
            **filters
        )

    def target_ion_update(self, **row):
        self.target_ions.update(**row)

    def target_ion_delete(self, **filters):
        self.target_ions.delete(**filters)

    # target isotopes
    def target_isotope_create(self, **row):
        self.target_isotopes.create(**row)

    def target_isotope_read(self, **filters):
        min_isotope_abundance = filters.pop(
            'min_isotope_abundance'
            )
        return self.target_isotopes.ge(
            'relative_abundance',
            min_isotope_abundance/100,
            **filters
            )

    def target_isotope_update(self, **row):
        self.target_isotopes.update(**row)

    def target_isotope_delete(self, **filters):
        self.target_isotopes.delete(**filters)

    # CONFIG

    # ionization mechanism
    def config_ion_mechanism_create(self, **row):
        self.config_ion_mechanisms.create(**row)

    def config_ion_mechanism_read(self, **filters):
        return self.config_ion_mechanisms.read(**filters)

    def config_ion_mechanism_update(self, **row):
        self.config_ion_mechanisms.update(**row)

    def config_ion_mechanism_delete(self, **filters):
        self.config_ion_mechanisms.delete(**filters)

    # TEMPLATES

    # attribute templates
    def attribute_template_list(self):
        return self.attribute_templates.read()

    def attribute_template_get(self, **kwargs):
        return self.attribute_templates.read(**kwargs)

    def attribute_template_insert(self, **kwargs):
        kwargs['id'] = kwargs['name']
        self.attribute_templates.insert(**kwargs)

    def attribute_template_delete(self, id):
        self.attribute_templates.delete(id)
