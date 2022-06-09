import json

from karsalib.logging import (
    NO_LOGGING_DEFAULT,
    parent_func_name,
)


class DbTable:
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

    # CRUD operations

    def create(self, **kwargs):
        self.insert(**kwargs)

    def read(self, **kwargs):
        # List records filtered by kwargs. With empty filter list all.
        sql = f"""
            SELECT * FROM {self.name}
            {self.where(kwargs)}
        """
        self.cur.execute(sql)
        self.con.commit()
        res = self._decode_values_list()
        return res

    def update(self, **kwargs):
        record_id = kwargs['id']
        if self.read(id=record_id):
            # TODO: It actually does REPLACE instead of UPDATE
            self.insert(**kwargs)
        else:
            raise ValueError(f"No record with id {record_id} found")

    def delete(self, **kwargs):
        ids = self.get_ids(**kwargs)
        sql = f"""
            DELETE FROM {self.name}
            {self.where(kwargs)}
        """
        self.cur.execute(sql)
        self.con.commit()
        return ids

    # other operations

    def insert(self, **kwargs):
        def dump(value):
            """If value is either of type list or dict, dump to JSON"""
            if isinstance(value, list) or isinstance(value, dict):
                return json.dumps(value)
            else:
                return value
        # kwargs must comply with the table schema
        cols, values = zip(*kwargs.items())
        values = [dump(value) for value in values]
        str_cols = ','.join(cols)
        str_values = ','.join('?' * len(values))
        sql = f"""
            INSERT OR REPLACE INTO {self.name}({str_cols})
            VALUES({str_values});
            """
        self.cur.execute(sql, values)
        self.con.commit()
        row_id = self.cur.lastrowid
        self.log(row_id, kwargs.get('id') or kwargs.get('name'))
        return row_id

    def between(self, column, min_value, max_value):
        sql = f"""
            SELECT * FROM {self.name}
            WHERE {column} BETWEEN '{min_value}' AND '{max_value}'
            ORDER BY {column};
        """
        self.cur.execute(sql)
        res = self._decode_values_list()
        return res

    def get_joined(self, table, left_on, right_on, **kwargs):
        sql = f"""
            SELECT * FROM {self.name} l
            LEFT JOIN {table} r
            ON l.{left_on} == r.{right_on}
            {self.where(kwargs).replace(" id ", " l.id ")}
        """
        self.cur.execute(sql)
        res = self._decode_values_list()
        return res

    def get_ids(self, **kwargs):
        rows = self.read(**kwargs)
        return [row['id'] for row in rows]

    def where(self, filters):
        exclude = (
            filters.pop('exclude')
            if 'exclude' in filters
            else None
        )
        res = []
        if filters:
            for col, val in filters.items():
                if isinstance(val, list):
                    if len(val) > 0:
                        vals = "(" + ", ".join(list(map(
                            lambda i: "'" + str(i) + "'", val
                        ))) + ")"
                        res.append(f"{col} IN {vals}")
                else:
                    res.append(f"{col} = '{val}'")
            if exclude:
                exclude = "(" + ", ".join(list(map(
                    lambda i: "'" + str(i) + "'", exclude
                ))) + ")"
                res.append(f"id NOT IN {exclude}")
            return 'WHERE ' + ' AND '.join(res)
        else:
            return ''
