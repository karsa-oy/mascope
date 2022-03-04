import sqlite3
from karsalib.logging import (
    NO_LOGGING_DEFAULT,
    parent_func_name,
)


class DBTable:
    schema = []
    keys = []
    sql_create = None

    def log(self, *arg):
        if not NO_LOGGING_DEFAULT:
            print(f"[{self.__class__.__name__}.{parent_func_name()}]", *arg)

    def _wrap_schema(self):
        s = [' '.join(s) for s in self.schema]
        return ', '.join(s)

    def __init__(self, db, name):
        self.con = db.con
        self.cur = db.cur
        self.name = name
        self.keys = [s[0] for s in self.schema]
        self.cur.execute(self.sql_create)
        self.con.commit()
        self.log(name)

    def _decode_values_list(self, vslist):
        res = []
        for vs in vslist:
            r = {}
            r.update((k,v) for k,v in zip(self.keys, vs))
            res.append(r)
        return res

    def get_all(self):
        sql = f""" SELECT * FROM {self.name}; """
        self.cur.execute(sql)
        self.con.commit()
        res = self._decode_values_list(self.cur)
        self.log(res)
        return res

    def create(self, **kwargs):
        if not self.get(id=kwargs['id']):
            self.insert(**kwargs)
        else:
            raise ValueError("Record already exists!")

    def insert(self, **kwargs):
        # kwargs must comply with the table schema
        cols, values = zip(*kwargs.items())
        str_cols = ','.join(cols)
        str_values = ','.join('?' * len(values))
        sql = f""" INSERT OR REPLACE INTO {self.name}({str_cols}) VALUES({str_values}); """
        self.cur.execute(sql, values)
        self.con.commit()
        row_id = self.cur.lastrowid
        self.log(row_id, kwargs.get('id') or kwargs.get('name'))
        return row_id

    def update(self, **kwargs):
        if self.get(id=kwargs['id']):
            # TODO: It actually does REPLACE instead of UPDATE
            self.insert(**kwargs)
        else:
            raise ValueError("Record does not exist!")

    def remove(self, item_id):
        sql = f""" DELETE FROM {self.name} WHERE id == {item_id}; """
        self.cur.execute(sql)
        self.con.commit()
        row_id = self.cur.lastrowid
        self.log(row_id)
        return row_id

    def between(self, column, min_value, max_value):
        sql = f""" SELECT * FROM {self.name} 
                   WHERE {column} BETWEEN '{min_value}' AND '{max_value}'
                   ORDER BY {column}; """
        self.cur.execute(sql)
        res = self._decode_values_list(self.cur)
        return res

    def get(self, **kwargs):
        def wrap_kwargs():
            res = []
            for k, v in kwargs.items():
                res.append(f"{k} = '{v}'")
            return ' AND '.join(res)
        sql = f""" SELECT * FROM {self.name} WHERE {wrap_kwargs()}; """
        self.cur.execute(sql)
        self.con.commit()
        res = self._decode_values_list(self.cur)
        return res

    def get_joined(self, table, left_on, right_on, **kwargs):
        def wrap_kwargs():
            res = []
            for k, v in kwargs.items():
                res.append(f"{k} = '{v}'")
            return ' AND '.join(res)

        sql = f""" SELECT * FROM {self.name} l 
                   LEFT JOIN {table} r
                        ON l.{left_on} == r.{right_on}
                    WHERE {wrap_kwargs()}; """
        self.cur.execute(sql)
        res = self._decode_values_list(self.cur)
        return res


class WorkspaceTable(DBTable):
    def __init__(self, db, name='workspaces'):
        self.schema = [
            ('id', 'varchar(16)', 'PRIMARY KEY'),
            ('name', 'text'),
            ('description', 'text'),
            ('attributes', 'json'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()}
            ); """
        super().__init__(db, name)


class SampleBatchTable(DBTable):
    def __init__(self, db, name='sample_batches'):
        self.schema = [
            ('id', 'varchar(16)', 'PRIMARY KEY'),
            ('workspaceId', 'varchar(16)', 'NOT NULL'),
            ('name', 'text'),
            ('description', 'text'),
            ('attributes', 'json'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()},
            FOREIGN KEY (workspaceId) REFERENCES workspaces (id)
            ); """
        super().__init__(db, name)


class SampleItemTable(DBTable):
    def __init__(self, db, name='sample_items'):
        self.schema = [
            ('id', 'varchar(16)', 'PRIMARY KEY'),
            ('batchId', 'varchar(16)', 'NOT NULL'),
            ('filename', 'varchar(256)', 'NOT NULL'),
            ('name', 'text'),
            ('description', 'text'),
            ('attributes', 'json'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()},
            FOREIGN KEY (batchId) REFERENCES sample_batches (id),
            FOREIGN KEY (filename) REFERENCES sample_files (id)
            ); """
        super().__init__(db, name)


class SampleFileTable(DBTable):
    def __init__(self, db, name='sample_files'):
        self.schema = [
            ('id', 'varchar(256)', 'PRIMARY KEY'),
            ('instrument', 'varchar(64)'),
            ('datetime', 'varchar(64)'),
            ('length', 'real'),
            ('range', 'json'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()}
            ); """
        super().__init__(db, name)



class SampleManagerDB:
    def log(self, *arg):
        if not NO_LOGGING_DEFAULT:
            print(f"[{self.__class__.__name__}.{parent_func_name()}]", *arg)

    def __init__(self, fname):
        self.con = None
        self.cur = None
        self.workspaces = None
        self.sample_batches = None
        self.sample_items = None
        self.sample_files = None
        self._connect(fname)

    def __del__(self):
        if self.con:
            self.con.close()

    def _connect(self, fname):
        self.log(fname)
        try:
            self.con = sqlite3.connect(fname)
            self.cur = self.con.cursor()
        except Exception as e:
            self.log(f'{e.__class__.__name__}({str(e)})')
            raise
        self.workspaces = WorkspaceTable(self)
        self.sample_batches = SampleBatchTable(self)
        self.sample_items = SampleItemTable(self)
        self.sample_files = SampleFileTable(self)

    # workspaces
    def workspace_list(self):
        return self.workspaces.get_all()

    def workspace_create(self, **kwargs):
        self.workspaces.create(**kwargs)

    def workspace_read(self, id):
        return self.workspaces.get(id=id)

    def workspace_update(self, **kwargs):
        self.workspaces.update(**kwargs)

    def workspace_delete(self, id):
        self.workspaces.remove(id=id)

    # sample batches
    def sample_batch_list(self, workspaceId):
        return self.sample_batches.get(workspaceId=workspaceId)
        
    def sample_batch_create(self, **kwargs):
        self.sample_batches.create(**kwargs)

    def sample_batch_read(self, id):
        return self.sample_batches.get(id=id)

    def sample_batch_update(self, **kwargs):
        self.sample_batches.update(**kwargs)

    def sample_batch_delete(self, id):
        self.sample_batches.remove(id=id)

    # sample items
    def sample_item_list(self, batchId):
        return self.sample_items.get_joined(
                    'sample_files',
                    'filename',
                    'id',
                    batchId=batchId
                    )
        
    def sample_item_create(self, **kwargs):
        if not self.sample_files.get(id=kwargs['id']):
            self.sample_files.create(id=kwargs['id'])
        self.sample_items.create(**kwargs)

    def sample_item_read(self, id):
        return self.sample_items.get_joined(
                    'sample_files',
                    'filename',
                    'id',
                    id=id
                    )

    def sample_item_update(self, **kwargs):
        # Update sample metadata and not sample file
        self.sample_items.update(**kwargs)

    def sample_item_delete(self, id):
        self.sample_items.remove(id=id)

    # sample files
    def sample_file_insert(self, **kwargs):
        self.sample_files.insert(**kwargs)

