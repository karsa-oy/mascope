pkgs=[
    {
        'name': 'runtime-lib',
        'path': ['libraries', 'mascope_runtime'],
        'install': 'poetry install',
        'run': None,
        'color': 'magenta'
    },
    {
        'name': 'standard-lib',
        'path': ['libraries', 'mascope_lib'],
        'install': 'poetry install',
        'run': None,
        'color': 'magenta'
    },
    {
        'name': 'hardware-lib',
        'path': ['libraries', 'mascope_hardware'],
        'install': 'poetry install',
        'run': None,
        'color': 'magenta'
    },
    {
        'name': 'api-lib',
        'path': ['libraries', 'mascope_api'],
        'install': 'poetry install',
        'run': None,
        'color': 'magenta'
    },
    {
        'name': 'tof-agent',
        'path': ['agents', 'tof_agent'],
        'install': 'poetry install',
        'run': 'poetry run mascope-tof-agent',
        'color': 'yellow'
    },
    {
        'name': 'file-mover',
        'path': ['agents', 'file_mover'],
        'install': 'poetry install',
        'run': 'poetry run mascope-file-mover',
        'color': 'yellow'
    },
    {
        'name': 'file-converter',
        'path': ['backend'],
        'install': None,
        'run': 'poetry run mascope-file-converter',
        'color': 'cyan'
    },
    {
        'name': 'backend',
        'path': ['backend'],
        'install': 'poetry install',
        'run': 'poetry run mascope-api',
        'color': 'blue'
    },
    {
        'name': 'frontend',
        'path': ['frontend'],
        'install': 'npm install',
        'run': 'npm run dev',
        'color': 'green'
    },
    {
        'name': 'cli',
        'path': ['tooling', 'cli'],
        'install': 'poetry install',
        'run': None,
        'color': 'white'
    },
]