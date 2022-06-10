from ..table import DbTable


class SampleBatchTable(DbTable):
    def __init__(self, db, name='sample_batches'):
        self.schema = [
            ('id', 'varchar(16)', 'PRIMARY KEY'),
            ('workspace_id', 'varchar(16)', 'NOT NULL'),
            ('name', 'text'),
            ('description', 'text'),
            ('attributes', 'json'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()},
            FOREIGN KEY (workspaceId) REFERENCES workspaces (id)
            ); """
        super().__init__(db, name)


class SampleItemTable(DbTable):
    def __init__(self, db, name='sample_items'):
        self.schema = [
            ('id', 'varchar(16)', 'PRIMARY KEY'),
            ('sample_batch_id', 'varchar(16)', 'NOT NULL'),
            ('filename', 'varchar(256)', 'NOT NULL'),
            ('title', 'varchar(256)', 'NOT NULL'),
            ('description', 'text'),
            ('attributes', 'json'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()},
            FOREIGN KEY (batchId) REFERENCES sample_batches (id),
            FOREIGN KEY (filename) REFERENCES sample_files (id)
            ); """
        super().__init__(db, name)


class SampleFileTable(DbTable):
    def __init__(self, db, name='sample_files'):
        self.schema = [
            ('id', 'varchar(256)', 'PRIMARY KEY'),
            ('filename', 'varchar(256)', 'NOT NULL'),
            ('title', 'varchar(256)'),
            ('instrument', 'varchar(64)'),
            ('datetime', 'varchar(64)'),
            ('length', 'real'),
            ('range', 'json'),
            ('description', 'text'),
            ('attributes', 'json'),
            ('mz_calibration', 'json'),
            ('datetime_utc', 'varchar(64)'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()}
            ); """
        super().__init__(db, name)
