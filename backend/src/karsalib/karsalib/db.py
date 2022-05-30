import json
import sqlite3
from nanoid import generate
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

    def _decode_values_list(self):
        def load(value):
            """Try to load value as JSON, and return the parsed object
            If not valid JSON, return the raw value"""
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return value
        rows = []
        columns = [description[0] for description in self.cur.description]
        for values in self.cur.fetchall():
            row = {}
            row.update(
                (column, load(value))
                for column, value in zip(columns, values)
                if column not in row
                )
            rows.append(row)
        return rows        

    def get_all(self):
        sql = f""" SELECT * FROM {self.name} ORDER BY id; """
        self.cur.execute(sql)
        self.con.commit()
        res = self._decode_values_list()
        self.log(res)
        return res

    def create(self, **kwargs):
        if not self.get(id=kwargs['id']):
            self.insert(**kwargs)
        else:
            raise ValueError("Record already exists!")

    def insert(self, **kwargs):
        def dump(value):
            """If value is either of type list or dict, dump to JSON"""
            if isinstance(value, list) or isinstance(value, dict):
                return json.dumps(value)
            else:
                return value
        # kwargs must comply with the table schema
        cols, values = zip(*kwargs.items())
        values = [ dump(value) for value in values ]
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

    def remove(self, row_id):
        sql = f""" DELETE FROM {self.name} WHERE id == '{row_id}'; """
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
        res = self._decode_values_list()
        return res

    def get(self, **kwargs):
        # List records filtered by kwargs. With empty filter list all. 
        def wrap_kwargs():
            res = []
            for k, v in kwargs.items():
                res.append(f"{k} = '{v}'")
            return ' AND '.join(res)
        filter = wrap_kwargs()
        if filter:
            sql = f""" SELECT * FROM {self.name} WHERE {wrap_kwargs()} ORDER BY id; """
        else:
            sql = f""" SELECT * FROM {self.name} ORDER BY id; """
        self.cur.execute(sql)
        self.con.commit()
        res = self._decode_values_list()
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
        res = self._decode_values_list()
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


class SampleFileTable(DBTable):
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


class AttributeTemplateTable(DBTable):
    def __init__(self, db, name='attribute_templates'):
        self.schema = [
            ('id', 'varchar(256)', 'PRIMARY KEY'),
            ('name', 'varchar(256)', 'NOT NULL'),
            ('type', 'varchar(64)'),
            ('template', 'json'),
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
        self.attribute_templates = None
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
        self.attribute_templates = AttributeTemplateTable(self)

    # workspaces
    def workspace_create(self, **row):
        self.workspaces.create(**row)

    def workspace_read(self, **filters):
        return self.workspaces.get(**filters)

    def workspace_update(self, **row):
        self.workspaces.update(**row)

    def workspace_delete(self, id):
        self.workspaces.remove(row_id=id)

    # sample batches
    def sample_batch_create(self, **row):
        self.sample_batches.create(**row)

    def sample_batch_read(self, **filters):
        return self.sample_batches.get(**filters)

    def sample_batch_update(self, **row):
        self.sample_batches.update(**row)

    def sample_batch_delete(self, id):
        self.sample_batches.remove(row_id=id)

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

    def sample_item_delete(self, id):
        self.sample_items.remove(row_id=id)

    def sample_item_get(self, **kwargs):
        return self.sample_items.get(**kwargs)

    def sample_item_insert(self, **kwargs):
        # creates or updates sample item
        self.sample_items.insert(**kwargs)

    def sample_item_get_schema(self):
        return [ 
            name for name,*_ 
            in self.sample_items.schema
        ]

    # sample files
    def sample_file_get(self, **kwargs):
        return self.sample_files.get(**kwargs)

    def sample_file_get_range(self, *args, **kwargs):
        return self.sample_files.between(*args, **kwargs)

    def sample_file_insert(self, **kwargs):
        self.sample_files.insert(**kwargs)

    def sample_file_get_schema(self):
        res = [name for name,*_ in self.sample_files.schema]
        return res

    # attribute templates
    def attribute_template_list(self):
        return self.attribute_templates.get_all()

    def attribute_template_get(self, **kwargs):
        return self.attribute_templates.get(**kwargs)

    def attribute_template_insert(self, **kwargs):
        kwargs['id'] = kwargs['name']
        self.attribute_templates.insert(**kwargs)

    def attribute_template_delete(self, id):
        self.attribute_templates.remove(id)

def gen_id(length = 16):
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890'
    return generate(alphabet, length)