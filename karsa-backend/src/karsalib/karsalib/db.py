import json
import sqlite3
import os
from karsalib.logging import (
    NO_DATA_LOGGING_DEFAULT,
    NO_LOGGING_DEFAULT,
    parent_func_name,
    this_func_name
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
        # self.con.commit()
        res = self._decode_values_list(self.cur)
        self.log(res)
        return res

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
        # self.con.commit()
        res = self._decode_values_list(self.cur)
        self.log(res)
        return res


class CatalogTable(DBTable):
    def __init__(self, db, name='catalog'):
        self.schema = [
            ('id', 'text', 'PRIMARY KEY'),
            ('name', 'text'),
            ('meta', 'text'),
            ('parent_id', 'text', 'NOT NULL'),
            ('sample_id', 'integer'),
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()},
            FOREIGN KEY (parent_id) REFERENCES catalog (id),
            FOREIGN KEY (sample_id) REFERENCES store (id)
            ); """
        super().__init__(db, name)

    def walk(self, item_id):
        sql = f""" SELECT *  FROM {self.name} WHERE id = '{item_id}' or parent_id = '{item_id}'; """
        self.cur.execute(sql)
        items = self._decode_values_list(self.cur)
        res = [None, [], []]
        for i in items:
            if i['id'] == item_id:
                res[0] = i
            elif i['sample_id'] is None:
                res[1].append(i)
            else:
                res[2].append(i)
        return res

    def _get_family_ids(self, parent_id, result_list):
        result_list.append(parent_id)
        sql = f""" SELECT id FROM '{self.name}' WHERE parent_id = '{parent_id}'; """
        self.cur.execute(sql)
        child_list = list(self.cur)
        for id, in child_list:
            if id == parent_id:
                continue
            self._get_family_ids(id, result_list)

    def remove(self, item_id):
        ids = []
        self._get_family_ids(item_id, ids)
        str_ids = ','.join('?' * len(ids))
        sql = f""" DELETE FROM {self.name} WHERE id IN ({str_ids}); """
        self.cur.execute(sql, ids)
        self.con.commit()
        self.log(ids)
        return ids


class StoreTable(DBTable):
    def __init__(self, db, name='store'):
        self.schema = [
            ('id', 'text', 'PRIMARY KEY'),
            ('filename', 'text'),
            ('instrument', 'text'),
            ('date', 'text'),
            ('time', 'text'),
            ('length', 'real'),
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
        self.store = None
        self.catalog = None
        self._connect(fname)
        self.catalog_mkdir('/')

    def __del__(self):
        if self.con:
            self.con.close()

    def _connect(self, fname):
        self.log(fname)
        try:
            self.con = sqlite3.connect(fname)
            self.cur = self.con.cursor()
        except Exception as e:
            self.log(e.__class__.__name__(str(e)))
            raise
        self.store = StoreTable(self)
        self.catalog = CatalogTable(self)

    def catalog_mkdir(self, path, attrs=None):
        # if self.catalog.get(id=path):
        #     return
        dpath, dname = os.path.split(path)
        if not dpath or dpath[0] != '/':
            raise Exception(f'[{this_func_name()}] Full path required: {path}')
        attrs = attrs or {'title': dname, 'description': ''}
        self.catalog.insert(id=path, parent_id=dpath, name=dname,
                            meta=json.dumps(attrs))

    def catalog_add(self, path, sample_id, attrs=None):
        # if self.catalog.get(id=path):
        #     raise FileExistsError(path)
        dpath, fname = os.path.split(path)
        if not dpath:
            raise Exception(f'[{this_func_name()}] Full path required: {path}')
        attrs = attrs or {'title': fname, 'description': ''}
        self.catalog.insert(id=path, parent_id=dpath, name=fname,
                            meta=json.dumps(attrs), sample_id=sample_id)

    def catalog_remove(self, path):
        self.catalog.remove(path)

    def store_add(self, **zarr_data):
        id = zarr_data.get('id') or zarr_data.get('filename')
        if id:
            new_sample_data = {**zarr_data, 'id': id}
        else:
            new_sample_data = zarr_data
        self.store.insert(**new_sample_data)

    def store_remove(self, item_id):
        self.store.remove(item_id)


if __name__ == '__main__':
    sm = SampleManagerDB(':memory:')
    # s_01 = sm.store.insert(id='sample_01', filename='sample_01')
    # s_02 = sm.store.insert(id='sample_02', filename='sample_02')
    # root_id = sm.catalog.insert(name='/', id=0, parent_id=0)
    # d_01 = sm.catalog.insert(name='d_01', parent_id=root_id)
    # d_02 = sm.catalog.insert(name='d_02', parent_id=root_id)
    # d_113 = sm.catalog.insert(name='d_113', parent_id=d_01)
    # d_114 = sm.catalog.insert(name='d_114', parent_id=d_01)
    # d_02_1 = sm.catalog.insert(name='d_02_1', parent_id=d_02)
    # f_02_1 = sm.catalog.insert(name='f_02_1', parent_id=d_02, sample_id=s_01)
    # f_113_1 = sm.catalog.insert(name='f_113_1', parent_id=d_113, sample_id=s_01)
    # f_02_2 = sm.catalog.insert(name='f_02_2', parent_id=d_02, sample_id=s_02)
    # sm.store.get_all()
    # sm.catalog.get_all()
    # sm.catalog.get(sample_id=s_01)
    # print('Root walk:', sm.catalog.walk(root_id))
    # print('Item walk:', sm.catalog.walk(d_02))
    # sm.catalog.remove(d_02)
    # sm.store.get_all()
    # sm.catalog.get_all()
    # print('parent_id between', root_id, d_02, list(sm.catalog.between('parent_id', root_id, d_02)))

    s_01 = sm.store_add(filename='sample_01')
    s_02 = sm.store_add(filename='sample_02')

    sm.catalog_mkdir('/d_1')
    sm.catalog_mkdir('/d_2')
    sm.catalog_mkdir('/d_1/d_11')
    sm.catalog_mkdir('/d_1/d_12')
    sm.catalog_mkdir('/d_1/d_12/d_121')
    sm.catalog_add('/d_2/f_21', s_01)
    sm.catalog_add('/d_1/d_12/f_121', s_01)
    sm.catalog_add('/d_1/d_11/f_112', s_02)
    sm.catalog_add('/d_1/d_12/f_122', s_02)

    sm.store.get_all()
    sm.catalog.get_all()
    sm.catalog.get(sample_id=s_01)

    print('Root walk:', sm.catalog.walk('/'))
    print('Item walk:', sm.catalog.walk('/d_1/d_12'))

    d11, d12 = ('/d_1/d_11', '/d_1/d_12')
    print('parent_id between', d11, d12, list(sm.catalog.between('parent_id', d11, d12)))

    sm.catalog_remove('/d_1/d_12/f_122')
    sm.catalog_remove('/d_1/d_12')
    sm.store.get_all()
    sm.catalog.get_all()

    print('parent_id between', d11, d12, list(sm.catalog.between('parent_id', d11, d12)))
