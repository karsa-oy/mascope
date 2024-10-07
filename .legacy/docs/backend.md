# Backend

### Description

This package contains the Mascope backend and related subpackages, written in Python. The dependencies are managed by [Poetry](https://python-poetry.org/). Each subpackage has their own poetry environment.

```
backend/
├───mascope_server/  # Mascope backend and related packages
│   ├───api/            # REST API
│   ├───api_sio/        # Custom socketio server
│   ├───db/             # Database & filestore
│   ├───service/        # File converter
│   └───main.py         # Main entrypoint
├───scripts/         # build scripts
├───tests/           # tests
└───pyproject.toml
```

### Setup Requirements

- [Python 3.10](https://www.python.org/downloads/release/python-31011/) - Python interpreter
- [Poetry](https://python-poetry.org/) - Python dependency manager

### Project setup with Poetry

This project uses [Poetry](https://python-poetry.org/); Poetry is an all-in-one Python project management tool. Poetry manages dependencies and project settings via a modern `pyproject.toml` file. It supports dependency locking via a `poetry.lock` file which pins the versions of all dependencies in the tree; **the `poetry.lock` file should be comitted in the repository and updated correctly whenever our dependencies change**. It also manages Python virtual environments for you.

Once you have Poetry installed, you can run the following commands in this folder:

- `poetry install` to install the code into a virtual env managed by poetry
- `poetry run <script-name>` to run a script; we have the following:
  - `python`: run interactive Python shell in the virtual environment
  - `mascope-api`: run Mascope backend
  - `mascope-file-converter`: run Mascope file converter service
  - `mascope-log-rotate`: run Mascope log rotate service

To manage dependencies:

- `poetry add/remove` to add or remove packages
- `poetry lock` will update the `poetry.lock` file;

### Compile and build distribution packages

To build the backend package, run `/scripts/build/build.cmd`. Refer to the README inside `/scripts/build` for more details.
