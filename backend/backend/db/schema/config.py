from ..table import DbTable


class ConfigIonMechanismTable(DbTable):
    def __init__(self, db, name='config_ion_mechanisms'):
        self.schema = [
            ('id', 'VARCHAR(8)', 'PRIMARY KEY'),
            ('polarity', 'VARCHAR(1)'),
            ('mechanism', 'VARCHAR(64)'),
            ('reagent', 'VARCHAR(64)')
        ]
        self.sql_create = f""" CREATE TABLE IF NOT EXISTS {name} (
            {self._wrap_schema()}
            ); """
        super().__init__(db, name)
