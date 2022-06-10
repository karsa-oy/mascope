from ..table import DbTable


class WorkspaceTable(DbTable):
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
