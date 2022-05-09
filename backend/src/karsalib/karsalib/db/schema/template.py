from ..table import DbTable


class AttributeTemplateTable(DbTable):
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