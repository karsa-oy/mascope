from ..table import DbTable


class TargetCollectionTable(DbTable):
    def __init__(self, db, name='target_collections'):
        self.schema = [
            ('id', 'VARCHAR(256)', 'PRIMARY KEY'),
            ('name', 'VARCHAR(256)', 'NOT NULL'),
            ('description', 'TEXT'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()}
            ); """
        super().__init__(db, name)


class TargetCompoundTable(DbTable):
    def __init__(self, db, name='target_compounds'):
        self.schema = [
            ('id', 'VARCHAR(32)', 'PRIMARY KEY'),
            ('name', 'VARCHAR(256)'),
            ('formula', 'VARCHAR(256)', 'NOT NULL'),
            ('cas_number', 'VARCHAR(12)'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()}
            ); """
        super().__init__(db, name)


class TargetIonTable(DbTable):
    def __init__(self, db, name='target_ions'):
        self.schema = [
            ('id', 'VARCHAR(32)', 'PRIMARY KEY'),
            ('target_compound_id', 'VARCHAR(32)', 'NOT NULL'),
            ('mechanism_id', 'VARCHAR(32)', 'NOT NULL'),
            ('formula', 'VARCHAR(256)', 'NOT NULL'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()}
            ,FOREIGN KEY (target_compound_id)
                REFERENCES target_compounds (id)
            ,FOREIGN KEY (mechanism_id)
                REFERENCES config_ion_mechanisms (id)
            ); """
        super().__init__(db, name)


class TargetIsotopeTable(DbTable):
    def __init__(self, db, name='target_isotopes'):
        self.schema = [
            ('id', 'VARCHAR(32)', 'PRIMARY KEY'),
            ('target_ion_id', 'VARCHAR(32)', 'NOT NULL'),
            ('mz', 'REAL', 'NOT NULL'),
            ('relative_abundance', 'REAL', 'NOT NULL')
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()}
            ,FOREIGN KEY (target_ion_id)
                REFERENCES target_ions (id)
            ); """
        super().__init__(db, name)


# internal relations


class TargetCompoundInTargetCollectionTable(DbTable):
    def __init__(self, db, name='target_compound_in_target_collection'):
        self.schema = [
            ('target_compound_id', 'VARCHAR(256)', 'NOT NULL'),
            ('target_collection_id', 'VARCHAR(256)', 'NOT NULL'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()}
            ,PRIMARY KEY
                (target_compound_id, target_collection_id)
            ,FOREIGN KEY (target_compound_id)
                REFERENCES target_compounds (id)
            ,FOREIGN KEY (target_collection_id)
                REFERENCES target_collections (id)
            ); """
        super().__init__(db, name)


# external relations


class TargetCollectionInSampleBatchTable(DbTable):
    def __init__(self, db, name='target_collection_in_sample_batch'):
        self.schema = [
            ('target_collection_id', 'VARCHAR(256)', 'NOT NULL'),
            ('sample_batch_id', 'VARCHAR(256)', 'NOT NULL'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()}
            ,PRIMARY KEY
                (target_collection_id, sample_batch_id)
            ,FOREIGN KEY (target_collection_id)
                REFERENCES target_collections (id)
            ,FOREIGN KEY (sample_batch_id)
                REFERENCES sample_batches (id)
            ); """
        super().__init__(db, name)
