# Backend

### Description

This package contains the Mascope backend and related subpackages, written in Python. The dependencies are managed by [Poetry](https://python-poetry.org/). Each subpackage has their own poetry environment.

```
mascope
├───agents
├───backend          # Mascope backend and related packages
│   ├───backend         # Backend
│   ├───docker          # Backend dockerization
│   ├───docs            # Backend documentation
│   ├───hardware        # Hardware interfaces
│   ├───lib             # Library
│   ├───scripts         # Build scripts
│   ├───tests           # Tests
│   └───vbox            # VirtualBox scripts
├───frontend
└───scripts
```

### Setup Requirements

- [Python 3.10](https://www.python.org/downloads/release/python-31011/) - Python interpreter
- [poetry](https://python-poetry.org/) - Python dependency manager

### Project setup with Poetry

This project uses [Poetry](https://python-poetry.org/); Poetry is an all-in-one Python project management tool. Poetry manages dependencies and project settings via a modern `pyproject.toml` file. It supports dependency locking via a `poetry.lock` file which pins the versions of all dependencies in the tree; **the `poetry.lock` file should be comitted in the repository and updated correctly whenever our dependencies change**. It also manages Python virtual environments for you.

Once you have Poetry installed, you can run the following commands in this folder:

- `poetry install` to install the code into a virtual env managed by poetry
- `poetry run <script-name>` to run a script; we have the following:
  - `python`: run interactive Python shell in the virtual environment
  - `mascope-api`: run Mascope backend
  - `file-converter`: run Mascope file converter service
  - `file-downloader`: run Mascope file downloader service
  - `log-rotate`: run Mascope log rotate service

To manage dependencies:

- `poetry add/remove` to add or remove packages
- `poetry lock` will update the `poetry.lock` file;

### Project setup with Docker

See the README at the monorepo root.

### Project setup with VirtualBox and Vagrant

1. Have VirtualBox and vagrant installed

2. go to vbox\backend folder

cd vbox\backend

1. run development setup for the project in VirtualBox virtual environment

vagrant up

### Compile and build distribution packages

To build the backend package, run `/scripts/build/build.cmd`. Refer to the README inside `/scripts/build` for more details.

### DEPRECATED: Project profiling

**NOTE: Could not manage to make `py-spy` work in the poetry environment. To be figured out.**

1. py-spy profiler comes along with dev.setup: https://github.com/benfred/py-spy
