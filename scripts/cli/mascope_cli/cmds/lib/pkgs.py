pkgs=[
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
        'name': 'frontend',
        'path': ['frontend'],
        'install': 'npm install',
        'run': 'npm run dev',
        'color': 'green'
    },
    {
        'name': 'backend',
        'path': ['backend'],
        'install': 'poetry install',
        'run': 'poetry run mascope-api',
        'color': 'blue'
    },
    {
        'name': 'cli',
        'path': ['scripts', 'cli'],
        'install': 'poetry install',
        'run': None,
        'color': 'white'
    },
]